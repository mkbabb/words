<template>
  <div
    :class="
      cn(
        'search-container relative z-50 mx-auto w-full origin-top transition-all duration-300 ease-out',
        props.shrinkPercentage > 0 && !isAnyHovered ? 'max-w-xs' : 'max-w-lg',
        className
      )
    "
    @mouseenter="handleContainerEnter"
    @mouseleave="handleContainerLeave"
  >
    <!-- Grid Layout for Consistent Widths -->
    <div class="pointer-events-auto grid grid-cols-1 gap-2">
      <!-- Search Bar -->
      <div
        :class="
          cn(
            'search-bar flex items-center gap-2 p-2',
            'border-border bg-background/20 border-2 backdrop-blur-3xl',
            'cartoon-shadow-sm hover-shadow-lift rounded-2xl',
            'transition-all duration-300 ease-out',
            props.shrinkPercentage > 0 && !isAnyHovered
              ? 'scale-100'
              : 'scale-100'
          )
        "
        @mouseenter="hoverStates.searchBar = true"
        @mouseleave="hoverStates.searchBar = false"
      >
        <!-- Mode Toggle -->
        <Transition name="shrink">
          <div
            v-if="!props.shrinkPercentage || isAnyHovered"
            class="flex items-center justify-center"
          >
            <FancyF
              :mode="mode"
              size="lg"
              clickable
              @toggle-mode="store.toggleMode()"
            />
          </div>
        </Transition>

        <!-- Search Input -->
        <input
          ref="searchInput"
          v-model="query"
          :placeholder="placeholder"
          class="placeholder:text-muted-foreground focus:ring-primary h-12 w-full rounded-xl bg-transparent px-4 py-2 text-base transition-all outline-none focus:ring-1"
          @keydown.enter="handleEnter"
          @keydown.down.prevent="navigateResults(1)"
          @keydown.up.prevent="navigateResults(-1)"
          @keydown.escape="closeDropdown"
          @focus="handleFocus"
          @blur="handleBlur"
          @input="handleInput"
        />

        <!-- Hamburger Button -->
        <Transition name="shrink">
          <button
            v-if="!props.shrinkPercentage || isAnyHovered"
            class="hover-lift flex h-12 w-12 items-center justify-center rounded-xl"
            @click="store.toggleControls()"
            @mousedown="hamburgerClickedRecently = true"
          >
            <div
              class="flex h-5 w-5 flex-col items-center justify-center space-y-1"
            >
              <span
                v-for="i in 3"
                :key="i"
                class="block h-0.5 w-4 bg-current transition-all duration-300"
                :class="getHamburgerLineClass(i)"
              />
            </div>
          </button>
        </Transition>

        <!-- Progress Bar -->
        <div
          v-if="store.loadingProgress > 0"
          class="absolute right-0 -bottom-1 left-0 h-1 overflow-hidden"
        >
          <div
            class="h-full rounded-full bg-gradient-to-r from-purple-600/80 via-purple-500/70 to-purple-600/80 transition-[width] duration-300"
            :style="{ width: `${store.loadingProgress}%` }"
          />
        </div>
      </div>

      <!-- Dropdowns Container (hidden on scroll unless hovered) -->
      <Transition name="grid-expand">
        <div
          v-if="shouldShowDropdownsContainer"
          class="dropdowns-container absolute top-full right-0 left-0 grid grid-cols-1 gap-2 pt-2"
          @mouseenter="hoverStates.dropdowns = true"
          @mouseleave="hoverStates.dropdowns = false"
        >
          <!-- Controls Dropdown -->
          <Transition name="dropdown">
            <div
              v-if="store.showControls"
              class="dropdown-element border-border bg-background/20 cartoon-shadow-sm overflow-hidden rounded-2xl border-2 backdrop-blur-3xl"
              @mouseenter="hoverStates.controls = true"
              @mouseleave="hoverStates.controls = false"
            >
              <!-- Search Mode Toggle -->
              <div class="border-border/50 border-t px-4 py-3">
                <h3 class="mb-3 text-sm font-medium">Search Mode</h3>
                <BouncyToggle
                  v-model="store.searchMode"
                  :options="[
                    { label: 'Word Search', value: 'word' },
                    { label: 'Wordlist Search', value: 'wordlist' },
                  ]"
                />
              </div>

              <!-- Sources (Word Search Mode) -->
              <div
                v-if="store.searchMode === 'word'"
                class="border-border/50 border-t px-4 py-3"
              >
                <h3 class="mb-3 text-sm font-medium">Sources</h3>
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="source in sources"
                    :key="source.id"
                    @click="store.toggleSource(source.id)"
                    :class="
                      cn(
                        'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200',
                        store.selectedSources.includes(source.id)
                          ? 'bg-primary text-primary-foreground shadow-sm'
                          : 'bg-muted text-muted-foreground hover:bg-muted/80'
                      )
                    "
                  >
                    <component :is="source.icon" :size="16" />
                    {{ source.name }}
                  </button>
                </div>
              </div>

              <!-- AI Suggestions -->
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

              <!-- Wordlist Selection -->
              <div
                v-if="store.searchMode === 'wordlist'"
                class="border-border/50 border-t px-4 py-3"
              >
                <h3 class="mb-3 text-sm font-medium">Select Wordlist</h3>
                <div class="space-y-2">
                  <button
                    v-for="wordlist in wordlists"
                    :key="wordlist"
                    @click="store.setWordlist(wordlist)"
                    :class="
                      cn(
                        'w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition-all duration-200',
                        store.selectedWordlist === wordlist
                          ? 'bg-primary text-primary-foreground shadow-sm'
                          : 'bg-muted text-muted-foreground hover:bg-muted/80'
                      )
                    "
                  >
                    {{ wordlist }}
                  </button>
                </div>
              </div>
            </div>
          </Transition>

          <!-- Search Results Dropdown -->
          <Transition name="dropdown">
            <div
              v-if="shouldShowDropdown"
              class="dropdown-element border-border bg-background/20 cartoon-shadow-sm overflow-hidden rounded-2xl border-2 backdrop-blur-3xl"
              @mouseenter="hoverStates.searchResults = true"
              @mouseleave="hoverStates.searchResults = false"
            >
              <!-- Loading State -->
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
                  <span class="text-muted-foreground text-sm"
                    >Searching...</span
                  >
                </div>
              </div>

              <!-- Search Results -->
              <div
                v-else-if="searchResults.length > 0"
                class="bg-background/20 max-h-64 overflow-y-auto backdrop-blur-3xl"
              >
                <button
                  v-for="(result, index) in searchResults"
                  :key="result.word"
                  :class="
                    cn(
                      'flex w-full items-center justify-between px-4 py-3 text-left transition-all duration-200',
                      'border-muted-foreground/50 active:scale-[0.98]',
                      index === selectedIndex
                        ? 'bg-accent/60 scale-[1.02] border-l-8 pl-5'
                        : 'border-l-0 pl-4'
                    )
                  "
                  @click="selectResult(result)"
                  @mouseenter="selectedIndex = index"
                >
                  <span
                    :class="
                      cn(
                        'transition-all',
                        index === selectedIndex && 'text-primary font-semibold'
                      )
                    "
                  >
                    {{ result.word }}
                  </span>
                  <div class="flex items-center gap-2 text-xs">
                    <span
                      :class="
                        cn(
                          'text-muted-foreground',
                          index === selectedIndex &&
                            'text-primary font-semibold'
                        )
                      "
                    >
                      {{ result.method }}
                    </span>
                    <span
                      :class="
                        cn(
                          'text-muted-foreground',
                          index === selectedIndex &&
                            'text-primary font-semibold'
                        )
                      "
                    >
                      {{ Math.round(result.score * 100) }}%
                    </span>
                  </div>
                </button>
              </div>

              <!-- No Results Messages -->
              <div
                v-else-if="!isSearching && query.length < 2"
                class="text-muted-foreground bg-background/50 p-4 text-center text-sm backdrop-blur-sm"
              >
                Type at least 2 characters to search...
              </div>
              <div
                v-else-if="!isSearching && query.length >= 2"
                class="text-muted-foreground bg-background/50 p-4 text-center text-sm backdrop-blur-sm"
              >
                No matches found
              </div>
            </div>
          </Transition>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  ref,
  computed,
  reactive,
  onMounted,
  onUnmounted,
  nextTick,
  watch,
} from 'vue';
import { useScroll } from '@vueuse/core';
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

// State
const query = ref(store.searchQuery || '');
const searchResults = ref<SearchResult[]>(
  store.sessionState?.searchResults || []
);
const isSearching = ref(false);
const selectedIndex = ref(store.searchSelectedIndex || 0);
const aiSuggestions = ref<string[]>([]);
const isFocused = ref(false);
const hamburgerClickedRecently = ref(false);
const hideDropdownsOnScroll = ref(true);

// Hover tracking
const hoverStates = reactive({
  container: false,
  searchBar: false,
  controls: false,
  searchResults: false,
  dropdowns: false,
});

// Computed
const isAnyHovered = computed(() =>
  Object.values(hoverStates).some(state => state)
);

const mode = computed(() => store.mode);
const placeholder = computed(() =>
  mode.value === 'dictionary'
    ? 'Enter a word to define...'
    : 'Enter a word to find synonyms...'
);

const showSearchResults = ref(false);
const shouldShowDropdown = computed(
  () =>
    showSearchResults.value &&
    query.value.length > 0 &&
    (searchResults.value.length > 0 ||
      isSearching.value ||
      query.value.length < 2)
);

// Updated computed for dropdowns container visibility
const shouldShowDropdownsContainer = computed(() => {
  // If scrolling and not hovering, hide dropdowns
  if (hideDropdownsOnScroll.value && !isAnyHovered.value) {
    return false;
  }
  // Otherwise show if controls or search results should be visible
  return store.showControls || shouldShowDropdown.value;
});

// Scroll handling
const { y } = useScroll(window);
const lastScrollY = ref(0);

// Watch scroll and update hideDropdownsOnScroll
watch(y, newY => {
  const scrollDelta = newY - lastScrollY.value;
  lastScrollY.value = newY;

  // Hide on scroll down, show on scroll up
  if (scrollDelta > 5) {
    hideDropdownsOnScroll.value = true;
  } else if (scrollDelta < -5) {
    hideDropdownsOnScroll.value = false;
  }
});

// Sources configuration
const sources = [
  { id: 'wiktionary', name: 'Wiktionary', icon: WiktionaryIcon },
  { id: 'oxford', name: 'Oxford', icon: OxfordIcon },
  { id: 'dictionary_com', name: 'Dictionary.com', icon: DictionaryIcon },
];

const wordlists = [
  'SAT Vocabulary',
  'GRE Advanced',
  'Academic Words',
  'Medical Terms',
];

// Refs
const searchInput = ref<HTMLInputElement>();

// Search timer
let searchTimer: ReturnType<typeof setTimeout> | undefined;

// Hamburger line classes
const getHamburgerLineClass = (index: number) => {
  if (!store.showControls) return 'translate-y-0 rotate-0';

  if (index === 1) return 'translate-y-1.5 rotate-45';
  if (index === 2) return 'opacity-0';
  if (index === 3) return '-translate-y-1.5 -rotate-45';
};

// Event handlers
const handleContainerEnter = () => {
  hoverStates.container = true;
  hideDropdownsOnScroll.value = false;
};

const handleContainerLeave = () => {
  hoverStates.container = false;
  setTimeout(() => {
    if (!isAnyHovered.value) {
      hideDropdownsOnScroll.value = true;
    }
  }, 300);
};

const handleFocus = () => {
  isFocused.value = true;
  showSearchResults.value = true;
  hideDropdownsOnScroll.value = false;

  if (
    store.sessionState?.searchResults?.length > 0 &&
    query.value.length >= 2
  ) {
    searchResults.value = store.sessionState.searchResults.slice(0, 8);
  }

  nextTick(() => {
    if (searchInput.value && store.searchCursorPosition) {
      const pos = Math.min(store.searchCursorPosition, query.value.length);
      searchInput.value.setSelectionRange(pos, pos);
    }
  });
};

const handleBlur = () => {
  if (hamburgerClickedRecently.value || isAnyHovered.value) {
    hamburgerClickedRecently.value = false;
    return;
  }

  isFocused.value = false;
  showSearchResults.value = false;

  // Re-enable scroll hide after blur
  setTimeout(() => {
    if (!isAnyHovered.value) {
      hideDropdownsOnScroll.value = true;
    }
  }, 200);
};

const handleInput = (event: Event) => {
  const input = event.target as HTMLInputElement;
  store.searchCursorPosition = input.selectionStart || 0;
  performSearch();
};

const performSearch = () => {
  clearTimeout(searchTimer);
  store.searchQuery = query.value;

  if (query.value.length > 0) {
    showSearchResults.value = true;
  }

  if (!query.value) {
    searchResults.value = [];
    isSearching.value = false;
    showSearchResults.value = false;
    return;
  }

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

const handleEnter = async () => {
  clearTimeout(searchTimer);

  if (searchResults.value.length > 0 && selectedIndex.value >= 0) {
    await selectResult(searchResults.value[selectedIndex.value]);
  } else if (query.value) {
    isFocused.value = false;
    store.searchQuery = query.value;
    store.hasSearched = true;
    await store.getDefinition(query.value);
  }
};

const selectResult = async (result: SearchResult) => {
  clearTimeout(searchTimer);
  query.value = result.word;
  store.searchQuery = result.word;
  isFocused.value = false;
  searchResults.value = [];
  store.hasSearched = true;
  await store.getDefinition(result.word);
};

const selectWord = (word: string) => {
  query.value = word;
  handleEnter();
};

const navigateResults = (direction: number) => {
  if (!shouldShowDropdown.value || searchResults.value.length === 0) return;

  selectedIndex.value = Math.max(
    0,
    Math.min(searchResults.value.length - 1, selectedIndex.value + direction)
  );

  store.searchSelectedIndex = selectedIndex.value;
};

const closeDropdown = () => {
  if (searchInput.value) {
    searchInput.value.blur();
  } else {
    handleBlur();
  }
};

// Click outside handler
const handleClickOutside = (event: Event) => {
  const target = event.target as Element;

  if (isAnyHovered.value) return;

  if (!target.closest('.search-container')) {
    handleBlur();
  }
};

// Mounted
onMounted(async () => {
  try {
    const history = await store.getHistoryBasedSuggestions();
    aiSuggestions.value = history.slice(0, 4);
  } catch {
    aiSuggestions.value = [];
  }

  document.addEventListener('click', handleClickOutside);
});

// Cleanup
onUnmounted(() => {
  clearTimeout(searchTimer);
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
/* Grid expand animation */
.grid-expand-enter-active,
.grid-expand-leave-active {
  transition:
    grid-template-rows 300ms ease-out,
    opacity 300ms ease-out;
}

.grid-expand-enter-from,
.grid-expand-leave-to {
  grid-template-rows: 0fr;
  opacity: 0;
}

.grid-expand-enter-to,
.grid-expand-leave-from {
  grid-template-rows: 1fr;
  opacity: 1;
}

/* Dropdown animation */
.dropdown-enter-active,
.dropdown-leave-active {
  transition:
    transform 300ms ease-out,
    opacity 300ms ease-out;
}

.dropdown-enter-from,
.dropdown-leave-to {
  transform: scaleY(0);
  opacity: 0;
  transform-origin: top;
}

.dropdown-enter-to,
.dropdown-leave-from {
  transform-origin: top;
  transform: scaleY(1);
  opacity: 1;
}

/* Shrink animation */
.shrink-enter-active,
.shrink-leave-active {
  transition: all 300ms ease-out;
}

.shrink-enter-from,
.shrink-leave-to {
  width: 0;
  opacity: 0;
  transform: scale(0);
}

.shrink-enter-to,
.shrink-leave-from {
  width: auto;
  opacity: 1;
  transform: scale(1);
}

/* Disable animations for reduced motion */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
