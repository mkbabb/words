<template>
  <!-- Main Container (UI Layer - No Filter) -->
  <div :class="cn('relative z-50 mx-auto w-full max-w-lg p-2', className)">
    <!-- Search Bar UI -->
    <div
      class="card-shadow bg-background border-border relative overflow-visible rounded-2xl border"
    >
      <!-- Search Input Area -->
      <div class="p-4">
        <div class="flex items-center justify-center gap-3">
          <!-- Dictionary/Thesaurus Toggle -->
          <div
            class="from-primary/10 flex h-12 w-12 cursor-pointer items-center justify-center transition-all duration-300 ease-out hover:scale-110 active:scale-95"
            @click="store.toggleMode()"
            :title="
              mode === 'dictionary'
                ? 'Switch to thesaurus mode'
                : 'Switch to dictionary mode'
            "
          >
            <FancyF :mode="mode" size="lg" />
          </div>

          <!-- Search Input -->
          <div class="relative flex-1">
            <div
              class="text-muted-foreground pointer-events-none absolute top-1/2 left-3 z-20 -translate-y-1/2 transform"
            >
              <Search :size="20" />
            </div>

            <input
              ref="searchInput"
              v-model="query"
              :placeholder="placeholder"
              autofocus
              class="bg-background placeholder:text-muted-foreground focus-visible:ring-ring focus:bg-background flex h-auto w-full rounded-xl px-3 py-3 pr-4 pl-10 text-base shadow-sm transition-all duration-200 focus-visible:ring-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
              @keydown.enter="handleEnter"
              @keydown.down.prevent="navigateResults(1)"
              @keydown.up.prevent="navigateResults(-1)"
              @keydown.escape="closeDropdown"
            />
          </div>
        </div>
      </div>

      <!-- AI Suggestions (inside card) -->
      <div v-if="!query && aiSuggestions.length > 0" class="px-4 pb-2">
        <hr class="border-border/50 p-2" />

        <div class="flex flex-wrap items-center justify-center gap-2">
          <Sparkles :size="18" />
          <Button
            v-for="word in aiSuggestions"
            :key="word"
            variant="outline"
            size="sm"
            class="rounded-xl text-xs transition-all duration-200 hover:font-semibold hover:opacity-80"
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
          class="absolute right-0 -bottom-2 left-0"
        >
          <div
            class="h-[3px] rounded-full bg-gradient-to-r from-purple-600/80 via-purple-500/70 to-purple-600/80"
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

    <div class="bg-background absolute top-full right-0 left-0 mt-2">
      <div
        ref="searchResultsDropdown"
        v-if="showDropdown"
        class="card-shadow bg-background border-border overflow-hidden rounded-2xl border"
      >
        <!-- Loading -->
        <div v-if="isSearching && searchResults.length === 0" class="p-4">
          <div class="flex items-center gap-2">
            <div class="flex gap-1">
              <span
                v-for="i in 3"
                :key="i"
                class="bg-primary/60 h-2 w-2 animate-bounce rounded-full"
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
              cn('cursor-pointer px-4 py-3 transition-all duration-200', {
                'bg-accent dark:bg-accent/80 border-primary text-muted-foreground border-l-6 pl-6 font-bold':
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
                    'text-primary/90 translate-x-1 font-bold':
                      index === selectedIndex,
                    'font-medium': index !== selectedIndex,
                  })
                "
                >{{ result.word }}</span
              >
              <div class="flex items-center gap-2">
                <span class="text-xs">{{ result.method }}</span>
                <span class="text-xs"
                  >{{ Math.round(result.score * 100) }}%</span
                >
              </div>
            </div>
          </div>
        </div>

        <!-- No Results -->
        <div
          v-else-if="!isSearching && query.length >= 2"
          class="text-muted-foreground p-4 text-center text-sm"
        >
          No matches found
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

watch(query, async newQuery => {
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
  handleEnter();
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
  document.addEventListener('click', e => {
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
