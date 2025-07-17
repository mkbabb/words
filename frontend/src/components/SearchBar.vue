<template>
  <div
    :class="
      cn(
        'relative z-50 mx-auto w-full transition-all duration-300 ease-out',
        props.shrinkPercentage > 0 ? 'max-w-sm p-1' : 'max-w-lg p-2',
        className
      )
    "
    @mouseenter="handleSearchBarHover(true)"
    @mouseleave="handleSearchBarHover(false)"
  >
    <!-- Main Search Bar Container -->
    <div class="relative m-0 w-full p-0">
      <!-- Search Bar -->
      <div
        :class="
          cn(
            'border-border bg-background/50 hover-shadow-lift transition-smooth cartoon-shadow-sm relative overflow-visible rounded-2xl border-2 backdrop-blur-3xl',
            props.shrinkPercentage > 0 ? 'scale-80' : 'scale-100'
          )
        "
      >
        <!-- Search Input Area -->
        <div class="flex items-center p-2">
          <!-- Mode Toggle with bouncy shrinking -->
          <div
            ref="modeToggleContainer"
            class="relative flex items-center justify-center overflow-hidden"
            :class="{
              'w-12 opacity-100': !(
                props.shrinkPercentage >= 0.5 && !isHovered
              ),
              'w-0 opacity-0': props.shrinkPercentage >= 0.5 && !isHovered,
            }"
            style="
              transition:
                width 0.6s cubic-bezier(0.34, 1.4, 0.64, 1),
                opacity 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.4);
            "
          >
            <div
              ref="modeToggleButton"
              class="flex h-12 w-12 items-center justify-center rounded-xl"
              :class="{
                'scale-100': !(props.shrinkPercentage >= 0.5 && !isHovered),
                'scale-0': props.shrinkPercentage >= 0.5 && !isHovered,
              }"
              style="
                transition: transform 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
              "
            >
              <FancyF
                :mode="mode"
                size="lg"
                clickable
                @toggle-mode="store.toggleMode()"
              />
            </div>
          </div>

          <!-- Search Input -->
          <input
            ref="searchInput"
            v-model="query"
            :placeholder="placeholder"
            autofocus
            class="placeholder:text-muted-foreground shadow-subtle transition-smooth focus-ring focus:ring-primary w-full rounded-xl px-4 py-2 text-base outline-none hover:shadow-sm focus:ring-1 disabled:cursor-not-allowed disabled:opacity-50"
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

          <!-- Hamburger Dropdown Button with bouncy shrinking -->
          <div
            ref="hamburgerContainer"
            data-hamburger
            class="relative flex items-center justify-center overflow-hidden"
            :class="{
              'w-12 opacity-100': !(
                props.shrinkPercentage >= 0.5 && !isHovered
              ),
              'w-0 opacity-0': props.shrinkPercentage >= 0.5 && !isHovered,
            }"
            style="
              transition:
                width 0.6s cubic-bezier(0.34, 1.4, 0.64, 1),
                opacity 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.4);
            "
          >
            <button
              ref="hamburgerButton"
              data-hamburger
              class="hover-lift flex h-12 w-12 items-center justify-center rounded-xl"
              :class="{
                'scale-100': !(props.shrinkPercentage >= 0.5 && !isHovered),
                'scale-0': props.shrinkPercentage >= 0.5 && !isHovered,
              }"
              style="
                transition: transform 0.8s cubic-bezier(0.34, 1.56, 0.64, 1);
              "
              @mousedown="handleHamburgerMouseDown"
              @click="store.toggleControls()"
              :title="store.showControls ? 'Hide controls' : 'Show controls'"
            >
              <div
                class="flex h-5 w-5 flex-col items-center justify-center space-y-1"
              >
                <span
                  class="block h-0.5 w-4 bg-current transition-all duration-300 ease-out"
                  :class="{
                    'translate-y-1.5 rotate-45': store.showControls,
                    'translate-y-0 rotate-0': !store.showControls,
                  }"
                />
                <span
                  class="block h-0.5 w-4 bg-current transition-all duration-300 ease-out"
                  :class="{
                    'opacity-0': store.showControls,
                    'opacity-100': !store.showControls,
                  }"
                />
                <span
                  class="block h-0.5 w-4 bg-current transition-all duration-300 ease-out"
                  :class="{
                    '-translate-y-1.5 -rotate-45': store.showControls,
                    'translate-y-0 rotate-0': !store.showControls,
                  }"
                />
              </div>
            </button>
          </div>
        </div>

        <!-- Enhanced Controls Section - positioned above search results -->
        <Transition
          enter-active-class="transition-all duration-300 ease-out"
          enter-from-class="opacity-0 scale-y-0 transform-gpu"
          enter-to-class="opacity-100 scale-y-100 transform-gpu"
          leave-active-class="transition-all duration-200 ease-in"
          leave-from-class="opacity-100 scale-y-100 transform-gpu"
          leave-to-class="opacity-0 scale-y-0 transform-gpu"
        >
          <div
            ref="controlsDropdown"
            v-if="store.showControls"
            class="bg-background/95 border-border cartoon-shadow-sm backdrop-blur-x absolute top-full right-0 left-0 z-10 mt-3 w-full origin-top overflow-hidden rounded-2xl border"
          >
            <!-- Mode Selection with Bouncy Toggle -->
            <div class="border-border/50 border-t px-4 py-3">
              <div class="mb-3 flex items-center justify-between">
                <h3 class="text-foreground text-sm font-medium">Search Mode</h3>
              </div>
              <BouncyToggle
                v-model="store.searchMode"
                :options="[
                  { label: 'Word Search', value: 'word' },
                  { label: 'Wordlist Search', value: 'wordlist' },
                ]"
              />
            </div>

            <!-- Source Selection (for word search mode) -->
            <div
              v-if="store.searchMode === 'word'"
              class="border-border/50 border-t px-4 py-3"
            >
              <div class="mb-3 flex items-center justify-between">
                <h3 class="text-foreground text-sm font-medium">Sources</h3>
              </div>
              <div class="flex flex-wrap gap-2">
                <button
                  @click="store.toggleSource('wiktionary')"
                  :class="[
                    'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200',
                    store.selectedSources.includes('wiktionary')
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'bg-muted text-muted-foreground hover:bg-muted/80',
                  ]"
                >
                  <WiktionaryIcon
                    :size="16"
                    class="transition-transform group-hover:scale-110"
                  />
                  Wiktionary
                </button>
                <button
                  @click="store.toggleSource('oxford')"
                  :class="[
                    'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200',
                    store.selectedSources.includes('oxford')
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'bg-muted text-muted-foreground hover:bg-muted/80',
                  ]"
                >
                  <OxfordIcon
                    :size="16"
                    class="transition-transform group-hover:scale-110"
                  />
                  Oxford
                </button>
                <button
                  @click="store.toggleSource('dictionary_com')"
                  :class="[
                    'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200',
                    store.selectedSources.includes('dictionary_com')
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'bg-muted text-muted-foreground hover:bg-muted/80',
                  ]"
                >
                  <DictionaryIcon
                    :size="16"
                    class="transition-transform group-hover:scale-110"
                  />
                  Dictionary.com
                </button>
              </div>
            </div>

            <!-- AI Suggestions (for word search mode, always visible) -->
            <div
              v-if="store.searchMode === 'word' && aiSuggestions.length > 0"
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

            <!-- Wordlist Selection (for wordlist search mode) -->
            <div
              v-if="store.searchMode === 'wordlist'"
              class="border-border/50 border-t px-4 py-3"
            >
              <div class="mb-3 flex items-center justify-between">
                <h3 class="text-foreground text-sm font-medium">
                  Select Wordlist
                </h3>
              </div>
              <div class="space-y-2">
                <button
                  v-for="wordlist in [
                    'SAT Vocabulary',
                    'GRE Advanced',
                    'Academic Words',
                    'Medical Terms',
                  ]"
                  :key="wordlist"
                  @click="store.setWordlist(wordlist)"
                  :class="[
                    'w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition-all duration-200',
                    store.selectedWordlist === wordlist
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'bg-muted text-muted-foreground hover:bg-muted/80',
                  ]"
                >
                  {{ wordlist }}
                </button>
              </div>
            </div>
          </div>
        </Transition>

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
    </div>

    <!-- Search Results Dropdown - positioned BELOW controls pane with dynamic height -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 scale-y-0 transform-gpu"
      enter-to-class="opacity-100 scale-y-100 transform-gpu"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100 scale-y-100 transform-gpu"
      leave-to-class="opacity-0 scale-y-0 transform-gpu"
    >
      <div
        ref="searchResultsDropdown"
        v-if="shouldShowDropdown"
        class="bg-background/95 shadow-card border-border cartoon-shadow-sm absolute right-0 left-0 z-30 origin-top overflow-hidden rounded-2xl border-2 backdrop-blur-xl"
        :style="searchResultsStyle"
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
          ref="searchResultsContainer"
          class="scrollbar-thin max-h-64 overflow-y-auto"
        >
          <button
            v-for="(result, index) in searchResults"
            :key="result.word"
            :class="[
              'flex w-full cursor-pointer items-center justify-between px-4 py-3 text-left transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]',
              index === selectedIndex
                ? 'bg-accent border-primary scale-[1.02] border-l-4 pl-5'
                : 'hover:bg-muted/50 border-l-2 border-transparent',
            ]"
            @click="selectResult(result)"
            @mouseenter="selectedIndex = index"
          >
            <span
              :class="[
                'transition-smooth',
                index === selectedIndex
                  ? 'text-primary font-semibold'
                  : 'font-medium',
              ]"
              >{{ result.word }}</span
            >
            <div
              :class="[
                'text-muted-foreground transition-smooth flex items-center gap-2 text-xs',
                index === selectedIndex
                  ? 'text-primary font-semibold'
                  : 'font-medium',
              ]"
            >
              <span>{{ result.method }}</span>
              <span>{{ Math.round(result.score * 100) }}%</span>
            </div>
          </button>
        </div>

        <!-- Type more message for short queries -->
        <div
          v-else-if="!isSearching && query.length < 2"
          class="text-muted-foreground p-4 text-center text-sm"
        >
          Type at least 2 characters to search...
        </div>

        <!-- No Results -->
        <div
          v-else-if="!isSearching && query.length >= 2"
          class="text-muted-foreground p-4 text-center text-sm"
        >
          No matches found
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { useScroll } from '@vueuse/core';
import { gsap } from 'gsap';
import { useAppStore } from '@/stores';
import type { SearchResult } from '@/types';
import Button from '@/components/ui/Button.vue';
import FancyF from '@/components/ui/icons/FancyF.vue';
import BouncyToggle from '@/components/ui/BouncyToggle.vue';
import { Sparkles } from 'lucide-vue-next';
import { cn } from '@/utils';
import WiktionaryIcon from '@/components/ui/icons/WiktionaryIcon.vue';
import OxfordIcon from '@/components/ui/icons/OxfordIcon.vue';
import DictionaryIcon from '@/components/ui/icons/DictionaryIcon.vue';

interface SearchBarProps {
  className?: string;
  shrinkPercentage?: number;
}

const props = withDefaults(defineProps<SearchBarProps>(), {
  shrinkPercentage: 0,
});

const store = useAppStore();

// Responsive styling based on shrink percentage
// Removed computed classes - moved to template

// State - Initialize from store
const query = ref(store.searchQuery || '');
const searchResults = ref<SearchResult[]>(
  store.sessionState?.searchResults || []
);
const isSearching = ref(false);
const selectedIndex = ref(store.searchSelectedIndex || 0);
const aiSuggestions = ref<string[]>([]);
const isFocused = ref(false);
const isHovered = ref(false);

// Scroll handling to hide controls
const { y } = useScroll(window);
const lastScrollY = ref(0);

// Track hamburger click to prevent search blur
const hamburgerClickedRecently = ref(false);

// Refs
const searchInput = ref<HTMLInputElement>();
const searchResultsDropdown = ref<HTMLElement>();
const searchResultsContainer = ref<HTMLElement>();
const controlsDropdown = ref<HTMLElement>();
const modeToggleContainer = ref<HTMLElement>();
const hamburgerContainer = ref<HTMLElement>();
const modeToggleButton = ref<HTMLButtonElement>();
const hamburgerButton = ref<HTMLButtonElement>();

// Dynamic height calculation using Vue reactivity
const controlsHeight = ref(0);

// Update controls height using Vue's reactivity
const updateControlsHeight = () => {
  nextTick(() => {
    controlsHeight.value = controlsDropdown.value?.clientHeight || 0;
  });
};

// Reactive computed for search results positioning
const searchResultsStyle = computed(() => ({
  top: `calc(100% + ${store.showControls ? controlsHeight.value : 0}px)`,
}));

// Timers
let searchTimer: ReturnType<typeof setTimeout> | undefined;

// Computed
const mode = computed(() => store.mode);
const placeholder = computed(() =>
  mode.value === 'dictionary'
    ? 'Enter a word to define...'
    : 'Enter a word to find synonyms...'
);

// Search results visibility state
const showSearchResults = ref(false);

// Computed dropdown visibility - show immediately when typing
const shouldShowDropdown = computed(() => {
  return (
    showSearchResults.value &&
    query.value.length > 0 &&
    (searchResults.value.length > 0 ||
      isSearching.value ||
      query.value.length < 2)
  );
});

// Handle focus
const handleFocus = () => {
  isFocused.value = true;
  showSearchResults.value = true;

  // Restore search results from store if available and query is long enough
  if (
    store.sessionState?.searchResults?.length > 0 &&
    query.value.length >= 2
  ) {
    searchResults.value = store.sessionState.searchResults.slice(0, 8);

    // Results will animate via CSS transitions
  }

  // Restore cursor position on focus
  nextTick(() => {
    if (searchInput.value && store.searchCursorPosition) {
      const pos = Math.min(store.searchCursorPosition, query.value.length);
      searchInput.value.setSelectionRange(pos, pos);
    }
  });
};

// Simple hide for search results
const hideSearchResults = () => {
  showSearchResults.value = false;
};

// Handle blur with search results animation
const handleBlur = () => {
  // Don't hide search results if hamburger was just clicked
  if (hamburgerClickedRecently.value) {
    hamburgerClickedRecently.value = false;
    return;
  }

  isFocused.value = false;
  hideSearchResults();
};

// Handle click outside to close dropdown with animation
const handleClickOutside = (event: Event) => {
  const target = event.target as Element;

  // Don't close if clicking on hamburger button or its children
  if (hamburgerButton.value && target.closest('[data-hamburger]')) {
    return;
  }

  // Check if click is outside the search bar container
  if (!target.closest('.max-w-lg')) {
    handleBlur();
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

  // Show dropdown immediately when typing (if there's any text)
  if (query.value.length > 0) {
    showSearchResults.value = true;
  }

  // Handle empty query
  if (!query.value) {
    searchResults.value = [];
    isSearching.value = false;
    hideSearchResults();
    return;
  }

  // Reset results if too short, but keep dropdown visible
  if (query.value.length < 2) {
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

      // Results will animate via CSS transitions
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

  // Update height if controls are already visible
  if (store.showControls) {
    updateControlsHeight();
  }

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
  if (searchInput.value) {
    searchInput.value.blur(); // This will trigger handleBlur with animation
  } else {
    handleBlur(); // Fallback to direct blur handling
  }
};

// Handle search bar hover for element expansion
const handleSearchBarHover = (hovered: boolean) => {
  isHovered.value = hovered;
};

// Handle hamburger mousedown to set flag before blur event
const handleHamburgerMouseDown = () => {
  hamburgerClickedRecently.value = true;

  // Reset the flag after a longer delay to ensure blur has time to check it
  setTimeout(() => {
    hamburgerClickedRecently.value = false;
  }, 200);
};

// Watch for controls visibility changes to measure height
watch(
  () => store.showControls,
  newValue => {
    if (newValue) {
      // Update height when controls become visible
      updateControlsHeight();
    }
    // Height automatically adjusts via computed property
  }
);

// Watch for AI suggestions changes to re-measure height
watch(
  () => aiSuggestions.value,
  () => {
    if (store.showControls) {
      updateControlsHeight();
    }
  },
  { flush: 'post' }
);

// Watch for search mode changes to re-measure height
watch(
  () => store.searchMode,
  () => {
    if (store.showControls) {
      updateControlsHeight();
    }
  },
  { flush: 'post' }
);

// Watch for scroll to hide controls
watch(y, newY => {
  const scrollDelta = newY - lastScrollY.value;
  lastScrollY.value = newY;

  // Hide controls when scrolling down
  if (scrollDelta > 5 && store.showControls) {
    store.showControls = false;
  }
});

// No watcher needed - reactive styling handles shrinking automatically

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
