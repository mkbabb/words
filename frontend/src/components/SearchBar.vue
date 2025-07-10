<template>
  <!-- Main Container (UI Layer - No Filter) -->
  <div :class="cn('relative w-full max-w-lg mx-auto z-50', className)">
    <!-- Search Bar UI -->
    <div
      class="card-shadow rounded-2xl bg-background border border-border relative overflow-visible"
    >
      <!-- Search Input Area -->
      <div class="p-4">
        <div class="flex items-center justify-center gap-3">
          <!-- Dictionary/Thesaurus Toggle -->
          <div
            class="bg-gradient-to-br from-primary/10 to-primary/5 rounded-xl cursor-pointer transition-all duration-300 ease-out hover:scale-110 active:scale-95 flex items-center justify-center w-12 h-12"
            @click="store.toggleMode()"
            :title="
              mode === 'dictionary'
                ? 'Switch to thesaurus mode'
                : 'Switch to dictionary mode'
            "
          >
            <FancyF :mode="mode" size="base" />
          </div>

          <!-- Search Input -->
          <div class="relative flex-1">
            <div
              class="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground pointer-events-none z-20"
            >
              <Search :size="20" />
            </div>

            <input
              ref="searchInput"
              v-model="query"
              :placeholder="placeholder"
              autofocus
              class="flex w-full rounded-xl bg-background px-3 py-3 text-base shadow-sm transition-all duration-200 placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 pl-10 pr-4 bg-muted/30 focus:bg-background h-auto"
              @keydown.enter="handleEnter"
              @keydown.down.prevent="navigateResults(1)"
              @keydown.up.prevent="navigateResults(-1)"
              @keydown.escape="closeDropdown"
            />
          </div>
        </div>
      </div>

      <!-- AI Suggestions (inside card) -->
      <div v-if="!query && aiSuggestions.length > 0" class="pb-2 px-4">
        <hr class="border-border/50 p-2" />

        <div class="flex flex-wrap gap-2 justify-center items-center">
          <Sparkles />
          <Button
            v-for="word in aiSuggestions"
            :key="word"
            variant="outline"
            size="sm"
            class="rounded-xl text-xs hover:opacity-80 hover:font-semibold transition-all duration-200"
            @click="selectWord(word)"
          >
            {{ word }}
          </Button>
        </div>
      </div>

      <!-- Progress Bar -->
      <Transition
        enter-active-class="transition-all duration-200 ease-out"
        enter-from-class="opacity-0 scale-y-0"
        enter-to-class="opacity-100 scale-y-100"
        leave-active-class="transition-all duration-150 ease-in"
        leave-from-class="opacity-100 scale-y-100"
        leave-to-class="opacity-0 scale-y-0"
      >
        <div
          v-if="store.loadingProgress > 0"
          class="absolute left-0 right-0 -bottom-2"
        >
          <div
            class="h-[3px] bg-gradient-to-r from-purple-600/80 via-purple-500/70 to-purple-600/80 rounded-full"
            :style="{
              width: `${store.loadingProgress}%`,
              boxShadow: '0 0 12px rgba(147, 51, 234, 0.4)',
            }"
            style="transition: width 0.3s ease-out"
          />
        </div>
      </Transition>
    </div>

    <!-- Search Results Dropdown -->
    <div class="relative">
      <div class="absolute left-0 right-0 top-full mt-2">
        <div
          ref="searchResultsDropdown"
          v-if="showDropdown"
          class="card-shadow rounded-2xl bg-background border border-border overflow-hidden"
        >
          <!-- Loading -->
          <div v-if="isSearching && searchResults.length === 0" class="p-4">
            <div class="flex items-center gap-2 text-muted-foreground">
              <div class="flex gap-1">
                <span
                  v-for="i in 3"
                  :key="i"
                  class="w-2 h-2 bg-primary/60 rounded-full animate-bounce"
                  :style="{ animationDelay: `${(i - 1) * 150}ms` }"
                />
              </div>
              <span class="text-sm">Searching...</span>
            </div>
          </div>

          <!-- Results -->
          <div
            v-else-if="searchResults.length > 0"
            class="max-h-64 overflow-y-auto"
          >
            <div
              v-for="(result, index) in searchResults"
              :key="result.word"
              :class="
                cn('px-4 py-3 cursor-pointer transition-all duration-200', {
                  'bg-accent dark:bg-accent/80 border-l-6 border-primary pl-6 font-bold':
                    index === selectedIndex,
                  'hover:bg-muted/50 border-l-4 border-transparent':
                    index !== selectedIndex,
                })
              "
              @click="selectResult(result)"
              @mouseenter="selectedIndex = index"
            >
              <div class="flex items-center justify-between">
                <span
                  :class="
                    cn('transition-all duration-200', {
                      'font-bold text-primary/90 translate-x-1':
                        index === selectedIndex,
                      'font-medium': index !== selectedIndex,
                    })
                  "
                  >{{ result.word }}</span
                >
                <div class="flex items-center gap-2">
                  <span class="text-xs text-muted-foreground">{{
                    result.method
                  }}</span>
                  <span class="text-xs font-medium text-primary"
                    >{{ Math.round(result.score * 100) }}%</span
                  >
                </div>
              </div>
            </div>
          </div>

          <!-- No Results -->
          <div
            v-else-if="!isSearching && query.length >= 2"
            class="p-4 text-center text-muted-foreground text-sm"
          >
            No matches found
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue';
import { useAppStore } from '@/stores';
import { cn } from '@/utils';
import type { SearchResult } from '@/types';
import Button from '@/components/ui/Button.vue';
import FancyF from '@/components/FancyF.vue';
import { Search, Sparkles } from 'lucide-vue-next';
import { gsap } from 'gsap';

interface SearchBarProps {
  className?: string;
}

defineProps<SearchBarProps>();

const store = useAppStore();

// State
const query = ref('');
const searchResults = ref<SearchResult[]>([]);
const showDropdown = ref(false);
const isSearching = ref(false);
const selectedIndex = ref(0);
const aiSuggestions = ref<string[]>([]);

// Refs
const searchInput = ref<HTMLInputElement>();
const searchResultsDropdown = ref<HTMLElement>();

// Timers
let searchTimer: ReturnType<typeof setTimeout> | undefined;
let lookupTimer: ReturnType<typeof setTimeout> | undefined;

// Computed
const mode = computed(() => store.mode);
const placeholder = computed(() =>
  mode.value === 'dictionary'
    ? 'Enter a word to define...'
    : 'Enter a word to find synonyms...'
);

// Initialize suggestions and focus
onMounted(async () => {
  const history = await store.getHistoryBasedSuggestions();

  aiSuggestions.value = history.slice(0, 4);

  // Focus the search input
  nextTick(() => {
    if (searchInput.value) {
      searchInput.value.focus();
    }
  });
});

// Watch query - SEARCH ON EVERY KEYSTROKE
watch(query, async (newQuery) => {
  clearTimeout(searchTimer);
  clearTimeout(lookupTimer);

  // Update store
  store.searchQuery = newQuery;

  // Reset if empty
  if (!newQuery || newQuery.length < 2) {
    searchResults.value = [];
    if (showDropdown.value) {
      animateSearchResultsOut();
      setTimeout(() => {
        showDropdown.value = false;
      }, 300); // Wait for animation to complete
    }
    isSearching.value = false;
    return;
  }

  // Show dropdown with loading state immediately
  if (!showDropdown.value) {
    showDropdown.value = true;
    nextTick(() => {
      animateSearchResultsIn();
    });
  }
  isSearching.value = true;

  // Call search API with debounce
  searchTimer = setTimeout(async () => {
    try {
      const results = await store.search(newQuery);
      searchResults.value = results.slice(0, 8);
      selectedIndex.value = 0;
    } catch (error) {
      console.error('Search error:', error);
      searchResults.value = [];
    } finally {
      isSearching.value = false;
    }
  }, 200);
});

// Handle enter key
const handleEnter = async () => {
  clearTimeout(searchTimer);
  clearTimeout(lookupTimer);

  if (searchResults.value.length > 0 && selectedIndex.value >= 0) {
    await selectResult(searchResults.value[selectedIndex.value]);
  } else if (query.value) {
    // Direct lookup
    closeDropdown();
    store.searchQuery = query.value;
    store.hasSearched = true;
    await store.getDefinition(query.value);
  }
};

// Select result
const selectResult = async (result: SearchResult) => {
  clearTimeout(lookupTimer);
  query.value = result.word;
  closeDropdown();

  store.searchQuery = result.word;
  store.hasSearched = true;
  await store.getDefinition(result.word);
};

// Select word from suggestions
const selectWord = (word: string) => {
  query.value = word;
  // Let watch handle the search
};

// Navigate results with keyboard
const navigateResults = (direction: number) => {
  if (!showDropdown.value || searchResults.value.length === 0) return;

  selectedIndex.value = Math.max(
    0,
    Math.min(searchResults.value.length - 1, selectedIndex.value + direction)
  );
};

// Close dropdown
const closeDropdown = () => {
  if (showDropdown.value) {
    animateSearchResultsOut();
    setTimeout(() => {
      showDropdown.value = false;
    }, 300);
  }
};

// GSAP Animation Functions
const animateSearchResultsIn = () => {
  if (searchResultsDropdown.value) {
    // Set initial state
    gsap.set(searchResultsDropdown.value, { opacity: 0, y: -10 });

    // Animate the dropdown
    gsap.to(searchResultsDropdown.value, {
      opacity: 1,
      y: 0,
      duration: 0.4,
      ease: 'power2.out',
    });
  }
};

const animateSearchResultsOut = () => {
  if (searchResultsDropdown.value) {
    // Animate dropdown out
    gsap.to(searchResultsDropdown.value, {
      opacity: 0,
      y: -5,
      duration: 0.2,
      ease: 'power2.in',
    });
  }
};

// Click outside to close
onMounted(() => {
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    if (!target.closest('.max-w-lg')) {
      closeDropdown();
    }
  });
});
</script>

<style scoped>
/* Disable GSAP animations during reduced motion */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
