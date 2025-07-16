<template>
  <div :class="cn('relative z-50 mx-auto w-full max-w-lg p-2', className)">
    <!-- Search Bar -->
    <div
      class="border-border bg-background/50 hover-shadow-lift transition-smooth cartoon-shadow-sm relative overflow-visible rounded-2xl border-2 backdrop-blur-3xl"
    >
      <!-- Search Input Area -->

      <div class="flex items-center p-2">
        <!-- Mode Toggle -->
        <button
          class="hover-lift flex h-12 w-12 items-center justify-center rounded-xl"
          @click="store.toggleMode()"
          :title="
            mode === 'dictionary'
              ? 'Switch to thesaurus mode'
              : 'Switch to dictionary mode'
          "
        >
          <FancyF :mode="mode" size="lg" />
        </button>

        <!-- Search Input -->
        <input
          ref="searchInput"
          v-model="query"
          :placeholder="placeholder"
          autofocus
          class="w-full rounded-xl px-4 py-2 text-xl text-base placeholder:text-muted-foreground shadow-subtle hover:shadow-sm transition-smooth focus-ring disabled:cursor-not-allowed disabled:opacity-50 focus:ring-primary outline-none focus:ring-1"
          @keydown.enter="handleEnter"
          @keydown.down.prevent="navigateResults(1)"
          @keydown.up.prevent="navigateResults(-1)"
          @keydown.escape="closeDropdown"
          @focus="handleFocus"
          @blur="handleBlur"
          @input="handleInput"
          @click="handleCursorChange"
          @keyup="handleCursorChange"
          @select="handleCursorChange"
        />
      </div>

      <!-- AI Suggestions -->
      <div
        v-if="!query && aiSuggestions.length > 0"
        class="border-border/50 border-t px-4 py-3"
      >
        <div class="flex flex-wrap items-center justify-center gap-2">
          <Sparkles class="text-muted-foreground" :size="16" />
          <Button
            v-for="word in aiSuggestions"
            :key="word"
            variant="outline"
            size="sm"
            class="hover-text-grow text-xs"
            @click="selectWord(word)"
          >
            {{ word }}
          </Button>
        </div>
      </div>

      <!-- Progress Bar -->
      <Transition
        enter-active-class="transition-smooth"
        enter-from-class="opacity-0 scale-y-0"
        enter-to-class="opacity-100 scale-y-100"
        leave-active-class="transition-smooth"
        leave-from-class="opacity-100 scale-y-100"
        leave-to-class="opacity-0 scale-y-0"
      >
        <div
          v-if="store.loadingProgress > 0"
          class="absolute right-0 -bottom-1 left-0 h-1 overflow-hidden"
        >
          <div
            class="shadow-glow h-full rounded-full bg-gradient-to-r from-purple-600/80 via-purple-500/70 to-purple-600/80 transition-[width] duration-300 ease-out"
            :style="{ width: `${store.loadingProgress}%` }"
          />
        </div>
      </Transition>
    </div>

    <!-- Search Results Dropdown -->
    <div
      ref="searchResultsDropdown"
      v-if="shouldShowDropdown"
      class="bg-background shadow-card border-border cartoon-shadow-sm absolute right-0 left-0 mt-2 overflow-hidden rounded-2xl border-2"
    >
      <!-- Loading State -->
      <div v-if="isSearching && searchResults.length === 0" class="p-4">
        <div class="flex items-center gap-2">
          <div class="flex gap-1">
            <span
              v-for="i in 3"
              :key="i"
              class="bg-primary/60 h-2 w-2 animate-bounce rounded-full"
              :class="`delay-${(i - 1) * 150}`"
            />
          </div>
          <span class="text-muted-foreground text-sm">Searching...</span>
        </div>
      </div>

      <!-- Search Results -->
      <div
        v-else-if="searchResults.length > 0"
        class="scrollbar-thin max-h-64 overflow-y-auto"
      >
        <button
          v-for="(result, index) in searchResults"
          :key="result.word"
          :class="[
            'flex items-center justify-between cursor-pointer px-4 py-3 transition-smooth w-full text-left',
            index === selectedIndex
              ? 'bg-accent border-primary border-l-4 pl-5'
              : 'hover:bg-muted/50 border-l-2 border-transparent'
          ]"
          @click="selectResult(result)"
          @mouseenter="selectedIndex = index"
        >
          <span :class="[
            'transition-smooth',
            index === selectedIndex ? 'text-primary font-semibold' : 'font-medium'
          ]">{{
            result.word
          }}</span>
          <div :class="[
            'text-muted-foreground flex items-center gap-2 text-xs transition-smooth',
            index === selectedIndex ? 'text-primary font-semibold' : 'font-medium'
          ]">
            <span>{{ result.method }}</span>
            <span>{{ Math.round(result.score * 100) }}%</span>
          </div>
        </button>
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
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useAppStore } from '@/stores';
import type { SearchResult } from '@/types';
import Button from '@/components/ui/Button.vue';
import FancyF from '@/components/FancyF.vue';
import { Sparkles } from 'lucide-vue-next';
import { cn } from '@/utils';

interface SearchBarProps {
  className?: string;
}

defineProps<SearchBarProps>();

const store = useAppStore();

// State - Initialize from store
const query = ref(store.searchQuery || '');
const searchResults = ref<SearchResult[]>(
  store.sessionState?.searchResults || []
);
const isSearching = ref(false);
const selectedIndex = ref(store.searchSelectedIndex || 0);
const aiSuggestions = ref<string[]>([]);
const isFocused = ref(false);

// Refs
const searchInput = ref<HTMLInputElement>();
const searchResultsDropdown = ref<HTMLElement>();

// Timers
let searchTimer: ReturnType<typeof setTimeout> | undefined;

// Computed
const mode = computed(() => store.mode);
const placeholder = computed(() =>
  mode.value === 'dictionary'
    ? 'Enter a word to define...'
    : 'Enter a word to find synonyms...'
);


// Computed dropdown visibility - only show when focused AND has valid results
const shouldShowDropdown = computed(() => {
  return (
    isFocused.value && query.value.length >= 2 && searchResults.value.length > 0
  );
});

// Handle focus
const handleFocus = () => {
  isFocused.value = true;

  // Restore search results from store if available and query is long enough
  if (
    store.sessionState?.searchResults?.length > 0 &&
    query.value.length >= 2
  ) {
    searchResults.value = store.sessionState.searchResults.slice(0, 8);
  }

  // Restore cursor position on focus
  nextTick(() => {
    if (searchInput.value && store.searchCursorPosition) {
      const pos = Math.min(store.searchCursorPosition, query.value.length);
      searchInput.value.setSelectionRange(pos, pos);
    }
  });
};

// Handle blur
const handleBlur = () => {
  // Delay blur to allow clicking on results
  setTimeout(() => {
    isFocused.value = false;
  }, 200);
};

// Handle click outside to close dropdown immediately
const handleClickOutside = (event: Event) => {
  const target = event.target as Element;
  // Check if click is outside the search bar container
  if (!target.closest('.max-w-lg')) {
    isFocused.value = false;
  }
};

// Handle cursor position changes (clicks, arrow keys, etc.)
const handleCursorChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  store.searchCursorPosition = input.selectionStart || 0;
};

// Handle input with cursor tracking
const handleInput = (event: Event) => {
  const input = event.target as HTMLInputElement;
  // Save cursor position on every input
  store.searchCursorPosition = input.selectionStart || 0;
  // Trigger search
  performSearch();
};

// Perform search with debounce
const performSearch = () => {
  clearTimeout(searchTimer);

  // Update store query
  store.searchQuery = query.value;

  // Reset if too short
  if (!query.value || query.value.length < 2) {
    searchResults.value = [];
    isSearching.value = false;
    return;
  }

  isSearching.value = true;

  searchTimer = setTimeout(async () => {
    try {
      const results = await store.search(query.value);
      searchResults.value = results.slice(0, 8);
      selectedIndex.value = 0;

      // Save results to store
      if (store.sessionState) {
        store.sessionState.searchResults = results;
      }
    } catch (error) {
      console.error('Search error:', error);
      searchResults.value = [];
    } finally {
      isSearching.value = false;
    }
  }, 200);
};

// Initialize on mount
onMounted(async () => {
  // Load suggestions
  try {
    const history = await store.getHistoryBasedSuggestions();
    aiSuggestions.value = history.slice(0, 4);
    console.log('AI suggestions loaded:', aiSuggestions.value);
  } catch {
    aiSuggestions.value = [];
  }

  // Add click outside listener
  document.addEventListener('click', handleClickOutside);

  // DON'T restore search results immediately - only when focused
  // This prevents dropdown from showing on refresh

  // DON'T auto-focus on mount - let user click to focus
  // This prevents dropdown from showing on refresh
});

// Handle enter key
const handleEnter = async () => {
  clearTimeout(searchTimer);

  if (searchResults.value.length > 0 && selectedIndex.value >= 0) {
    await selectResult(searchResults.value[selectedIndex.value]);
  } else if (query.value) {
    // Direct lookup
    isFocused.value = false;
    store.searchQuery = query.value;
    store.hasSearched = true;
    await store.getDefinition(query.value);
  }
};

// Select result
const selectResult = async (result: SearchResult) => {
  clearTimeout(searchTimer);
  query.value = result.word;
  store.searchQuery = result.word;

  // Clear dropdown
  isFocused.value = false;
  searchResults.value = [];

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
  if (!shouldShowDropdown.value || searchResults.value.length === 0) return;

  selectedIndex.value = Math.max(
    0,
    Math.min(searchResults.value.length - 1, selectedIndex.value + direction)
  );

  // Save selected index to store
  store.searchSelectedIndex = selectedIndex.value;
};

// Close dropdown
const closeDropdown = () => {
  isFocused.value = false;
  if (searchInput.value) {
    searchInput.value.blur();
  }
};

// Cleanup on unmount
onUnmounted(() => {
  clearTimeout(searchTimer);
  document.removeEventListener('click', handleClickOutside);
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
