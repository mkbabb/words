<template>
  <div :class="cn('relative z-50 mx-auto w-full max-w-lg p-2', className)">
    <!-- Search Bar -->
    <div class="relative overflow-visible rounded-2xl bg-background shadow-card border-2 border-border hover-shadow-lift transition-smooth">
      <!-- Search Input Area -->
      <div class="p-4">
        <div class="flex items-center gap-3">
          <!-- Mode Toggle -->
          <button
            class="h-12 w-12 flex items-center justify-center rounded-xl hover-lift"
            @click="store.toggleMode()"
            :title="mode === 'dictionary' ? 'Switch to thesaurus mode' : 'Switch to dictionary mode'"
          >
            <FancyF :mode="mode" size="lg" />
          </button>

          <!-- Search Input -->
          <div class="relative flex-1">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" :size="20" />
            <input
              ref="searchInput"
              v-model="query"
              :placeholder="placeholder"
              autofocus
              :class="inputClasses + ' focus:ring-1 focus:ring-primary outline-none'"
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
        </div>
      </div>

      <!-- AI Suggestions -->
      <div v-if="!query && aiSuggestions.length > 0" class="border-t border-border/50 px-4 py-3">
        <div class="flex flex-wrap items-center justify-center gap-2">
          <Sparkles class="text-muted-foreground" :size="16" />
          <Button
            v-for="word in aiSuggestions"
            :key="word"
            variant="outline"
            size="sm"
            class="text-xs hover-text-grow"
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
            class="h-full rounded-full bg-gradient-to-r from-purple-600/80 via-purple-500/70 to-purple-600/80 shadow-glow transition-[width] duration-300 ease-out"
            :style="{ width: `${store.loadingProgress}%` }"
          />
        </div>
      </Transition>
    </div>

    <!-- Search Results Dropdown -->
    <div
      ref="searchResultsDropdown"
      v-if="shouldShowDropdown"
      class="absolute mt-2 right-0 left-0 rounded-2xl bg-background shadow-card border-2 border-border overflow-hidden"
    >
      <!-- Loading State -->
      <div v-if="isSearching && searchResults.length === 0" class="p-4">
        <div class="flex items-center gap-2">
          <div class="flex gap-1">
            <span
              v-for="i in 3"
              :key="i"
              class="h-2 w-2 rounded-full bg-primary/60 animate-bounce"
              :class="`delay-${(i - 1) * 150}`"
            />
          </div>
          <span class="text-sm text-muted-foreground">Searching...</span>
        </div>
      </div>

      <!-- Search Results -->
      <div
        v-else-if="searchResults.length > 0"
        class="max-h-64 overflow-y-auto scrollbar-thin"
      >
        <button
          v-for="(result, index) in searchResults"
          :key="result.word"
          :class="getResultClasses(index === selectedIndex)"
          @click="selectResult(result)"
          @mouseenter="selectedIndex = index"
          class="w-full text-left"
        >
          <span :class="getResultTextClasses(index === selectedIndex)">{{ result.word }}</span>
          <div :class="getResultTextClasses(index === selectedIndex) + ' flex items-center gap-2 text-xs text-muted-foreground'">
            <span>{{ result.method }}</span>
            <span>{{ Math.round(result.score * 100) }}%</span>
          </div>
        </button>
      </div>

      <!-- No Results -->
      <div
        v-else-if="!isSearching && query.length >= 2"
        class="p-4 text-center text-sm text-muted-foreground"
      >
        No matches found
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useAppStore } from '@/stores';
import { cn } from '@/utils';
import type { SearchResult } from '@/types';
import Button from '@/components/ui/Button.vue';
import FancyF from '@/components/FancyF.vue';
import { Search, Sparkles } from 'lucide-vue-next';
import { cva } from 'class-variance-authority';

interface SearchBarProps {
  className?: string;
}

defineProps<SearchBarProps>();

const store = useAppStore();

// Input styling with CVA
const inputVariants = cva([
  'w-full rounded-xl',
  'px-3 py-3 pl-10 pr-4',
  'text-base bg-background',
  'placeholder:text-muted-foreground',
  'shadow-subtle hover:shadow-sm',
  'transition-smooth focus-ring',
  'disabled:cursor-not-allowed disabled:opacity-50'
]);

const inputClasses = computed(() => inputVariants());

// State - Initialize from store
const query = ref(store.searchQuery || '');
const searchResults = ref<SearchResult[]>(store.sessionState?.searchResults || []);
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

// Result item classes
const getResultClasses = (isSelected: boolean) => {
  return cn(
    'flex items-center justify-between',
    'px-4 py-3 cursor-pointer',
    'transition-smooth',
    isSelected
      ? 'bg-accent border-l-4 border-primary pl-5'
      : 'hover:bg-muted/50 border-l-2 border-transparent'
  );
};

const getResultTextClasses = (isSelected: boolean) => {
  return cn(
    'transition-smooth',
    isSelected ? 'font-semibold text-primary' : 'font-medium'
  );
};

// Computed dropdown visibility - only show when focused AND has valid results
const shouldShowDropdown = computed(() => {
  return isFocused.value && query.value.length >= 2 && searchResults.value.length > 0;
});

// Handle focus
const handleFocus = () => {
  isFocused.value = true;
  
  // Restore search results from store if available and query is long enough
  if (store.sessionState?.searchResults?.length > 0 && query.value.length >= 2) {
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
