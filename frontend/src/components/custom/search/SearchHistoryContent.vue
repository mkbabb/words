<template>
  <!-- Collapsed View -->
  <Transition
    enter-active-class="transition-all duration-500 ease-apple-smooth"
    leave-active-class="transition-all duration-400 ease-apple-smooth"
    enter-from-class="opacity-0 scale-95"
    enter-to-class="opacity-100 scale-100"
    leave-from-class="opacity-100 scale-100"
    leave-to-class="opacity-0 scale-95"
    mode="out-in"
  >
    <div v-if="collapsed" key="collapsed" class="flex h-full w-full flex-col">
      <!-- Collapsed view - compact cards -->
      <div class="relative min-h-0 flex-1">
        <div class="absolute inset-0">
          <div class="max-h-full space-y-1 overflow-y-auto overscroll-contain">
            <TransitionGroup
              enter-active-class="transition-all duration-400 ease-apple-smooth"
              leave-active-class="transition-all duration-300 ease-apple-smooth"
              enter-from-class="opacity-0 -translate-y-4 scale-95"
              enter-to-class="opacity-100 translate-y-0 scale-100"
              leave-from-class="opacity-100 translate-y-0 scale-100"
              leave-to-class="opacity-0 translate-y-4 scale-95"
              move-class="transition-transform duration-300 ease-apple-smooth"
              tag="div"
              class="space-y-1"
            >
              <div
                v-for="entry in limitedLookups"
                :key="entry.id"
              >
                <HoverCard
                  :open-delay="150"
                  :close-delay="50"
                >
                  <HoverCardTrigger>
                    <div
                      :class="
                        cn(
                          'group relative w-full cursor-pointer overflow-hidden rounded-lg transition-all duration-300 ease-apple-smooth',
                          'bg-background border-border border shadow-sm',
                          'hover:bg-accent hover:shadow-md hover:scale-105'
                        )
                      "
                      @click="lookupWord(entry.word)"
                    >
                      <div class="flex items-center justify-center px-2 py-2">
                        <span class="text-xs font-bold tracking-wider uppercase">
                          {{ entry.word.substring(0, 2) }}
                        </span>
                      </div>
                    </div>
                  </HoverCardTrigger>
                  <HoverCardContent class="w-80 max-h-96" side="right" :side-offset="8">
                    <div class="space-y-3">
                      <!-- Word Header -->
                      <div class="flex items-center justify-between">
                        <h3 class="text-base font-semibold">{{ entry.word }}</h3>
                        <span class="text-muted-foreground text-xs">
                          {{ formatDate(entry.timestamp) }}
                        </span>
                      </div>
                      
                      <!-- Pronunciation -->
                      <div v-if="entry.entry.pronunciation?.phonetic" class="text-sm text-muted-foreground">
                        {{ entry.entry.pronunciation.phonetic }}
                      </div>
                      
                      <!-- Separator -->
                      <hr class="border-border/30">
                      
                      <!-- Definitions -->
                      <div class="max-h-48 overflow-y-auto overflow-x-hidden space-y-1">
                        <div
                          v-for="(def, defIndex) in entry.entry.definitions"
                          :key="defIndex"
                          class="text-sm break-words"
                        >
                          <span class="font-medium text-accent-foreground">{{ def.part_of_speech }}</span>
                          <span class="text-muted-foreground ml-2">{{ def.text }}</span>
                        </div>
                      </div>
                      
                      <!-- Metadata -->
                      <div v-if="entry.entry.lookup_count" class="flex justify-between text-xs text-muted-foreground border-t border-border/30 pt-2">
                        <span v-if="entry.entry.lookup_count">Lookups: {{ entry.entry.lookup_count }}</span>
                      </div>
                    </div>
                  </HoverCardContent>
                </HoverCard>
              </div>
            </TransitionGroup>
          </div>
        </div>
      </div>
    </div>

    <!-- Expanded View -->
    <div v-else key="expanded" class="space-y-1">
      <!-- Expanded view - simple scrollable list -->
      <div v-if="recentLookups.length > 0" class="space-y-1">
        <TransitionGroup
          enter-active-class="transition-all duration-400 ease-apple-smooth"
          leave-active-class="transition-all duration-300 ease-apple-smooth"
          enter-from-class="opacity-0 -translate-x-4"
          enter-to-class="opacity-100 translate-x-0"
          leave-from-class="opacity-100 translate-x-0"
          leave-to-class="opacity-0 translate-x-4"
          move-class="transition-transform duration-300 ease-apple-smooth"
          tag="div"
          class="space-y-1"
        >
          <div
            v-for="entry in recentLookups"
            :key="entry.id"
            :class="
              cn(
                'group flex cursor-pointer items-center justify-between rounded-lg px-2 py-2 transition-all duration-300 ease-apple-smooth',
                'hover:bg-accent hover:pl-3 hover:scale-[1.02]'
              )
            "
            @click="lookupWord(entry.word)"
          >
            <div class="flex min-w-0 items-center gap-3">
              <History :size="14" class="text-muted-foreground shrink-0" />
              <span class="truncate text-sm">{{ entry.word }}</span>
            </div>
            <span
              class="text-muted-foreground text-xs opacity-0 transition-opacity duration-200 group-hover:opacity-100"
            >
              {{ formatDate(entry.timestamp) }}
            </span>
          </div>
        </TransitionGroup>
      </div>

      <div v-else class="py-4 text-center">
        <p class="text-muted-foreground text-xs">No recent lookups</p>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useStores } from '@/stores';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';
import { formatDate, cn } from '@/utils';
import { History } from 'lucide-vue-next';
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui';

interface Props {
  collapsed: boolean;
}

defineProps<Props>();

const { history } = useStores();
const searchBarStore = useSearchBarStore();
const recentLookups = computed(() => history.recentLookups);

// Create orchestrator for API operations
const orchestrator = useSearchOrchestrator({
    query: computed(() => searchBarStore.searchQuery)
});

const limitedLookups = computed(() => {
  return recentLookups.value.slice(0, 20); // Limit to prevent performance issues
});

const lookupWord = async (word: string) => {
  searchBarStore.setQuery(word);
  searchBarStore.setDirectLookup(true);
  try {
    if (searchBarStore.getSubMode('lookup') === 'thesaurus') {
      await orchestrator.getThesaurusData(word);
    } else {
      await orchestrator.getDefinition(word);
    }
  } finally {
    searchBarStore.setDirectLookup(false);
  }
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
  background: hsl(var(--muted));
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
