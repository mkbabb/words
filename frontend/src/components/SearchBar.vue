<template>
  <div
    ref="searchContainer"
    :class="[
      'search-container relative z-50 mx-auto origin-top',
      'w-full',
      props.className
    ]"
    :style="containerStyle"
    @mouseenter="handleMouseEnter"
    @mouseleave="handleMouseLeave"
  >
    <!-- Main Layout -->
    <div class="pointer-events-auto relative">
      <!-- Search Bar -->
      <div
        ref="searchBarElement"
        :class="[
          'search-bar flex items-center gap-2 p-2 h-16',
          'border-border bg-background/20 border-2 backdrop-blur-3xl',
          'cartoon-shadow-sm hover-shadow-lift rounded-2xl'
        ]"
      >
        <!-- Mode Toggle -->
        <div
          :class="[
            'flex items-center justify-center overflow-hidden transition-all duration-300 ease-out'
          ]"
          :style="{ 
            opacity: iconOpacity,
            transform: `scale(${0.9 + iconOpacity * 0.1})`,
            pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
            width: `${iconOpacity * 48}px`,
            marginRight: `${iconOpacity * 8}px`
          }"
        >
          <FancyF
            :mode="mode"
            size="lg"
            clickable
            @toggle-mode="handleModeToggle"
          />
        </div>

        <!-- Search Input -->
        <input
          ref="searchInput"
          v-model="query"
          :placeholder="placeholder"
          :class="[
            'placeholder:text-muted-foreground focus:ring-primary h-12 flex-1 min-w-0 rounded-xl bg-transparent py-2 text-base outline-none focus:ring-1 text-ellipsis overflow-hidden whitespace-nowrap transition-all duration-300 ease-out'
          ]"
          :style="{
            paddingLeft: iconOpacity > 0.1 ? '1rem' : '1.5rem',
            paddingRight: iconOpacity > 0.1 ? '1rem' : '1.5rem'
          }"
          @keydown.enter="handleEnter"
          @keydown.down.prevent="navigateResults(1)"
          @keydown.up.prevent="navigateResults(-1)"
          @keydown.escape="handleEscape"
          @focus="handleFocus"
          @blur="handleBlur"
          @input="handleInput"
        />

        <!-- Regenerate Button - Only shows when we have a current entry and in word search mode -->
        <div
          v-if="store.currentEntry && store.searchMode === 'word'"
          :class="[
            'flex items-center justify-center overflow-hidden transition-all duration-300 ease-out'
          ]"
          :style="{ 
            opacity: iconOpacity,
            transform: `scale(${0.9 + iconOpacity * 0.1})`,
            pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
            width: `${iconOpacity * 48}px`,
            marginLeft: `${iconOpacity * 8}px`
          }"
        >
          <button
            @click="handleForceRegenerate"
            :class="[
              'flex h-10 w-10 items-center justify-center rounded-lg',
              store.forceRefreshMode ? 'bg-primary/20 text-primary' : '',
              'hover:bg-muted/50 active:scale-95'
            ]"
            style="transition: background-color 150ms ease-out, transform 150ms ease-out"
            :title="store.forceRefreshMode ? 'Force refresh mode ON - Next lookup will regenerate' : 'Toggle force refresh mode'"
          >
            <RefreshCw 
              :size="20" 
              :style="{
                transform: `rotate(${regenerateRotation}deg)`,
                transition: 'transform 700ms cubic-bezier(0.175, 0.885, 0.32, 1.4)'
              }"
            />
          </button>
        </div>

        <!-- Hamburger Button -->
        <div
          :class="[
            'overflow-hidden transition-all duration-300 ease-out'
          ]"
          :style="{ 
            opacity: iconOpacity,
            transform: `scale(${0.9 + iconOpacity * 0.1})`,
            pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
            width: `${iconOpacity * 48}px`,
            marginLeft: `${iconOpacity * 8}px`
          }"
        >
          <HamburgerIcon
            :is-open="store.showControls"
            @toggle="handleHamburgerClick"
          />
        </div>

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

      <!-- Dropdowns Container - Absolutely positioned to prevent content shifting -->
      <div class="absolute top-full left-0 right-0 z-50 pt-2">
        <!-- Controls Dropdown -->
        <Transition
          enter-active-class="transition-all duration-300 ease-apple-bounce"
          leave-active-class="transition-all duration-300 ease-apple-bounce"
          enter-from-class="opacity-0 scale-95 -translate-y-4"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-from-class="opacity-100 scale-100 translate-y-0"
          leave-to-class="opacity-0 scale-95 -translate-y-4"
        >
          <div
            v-if="store.showControls"
            class="dropdown-element border-border bg-background/20 cartoon-shadow-sm mb-2 rounded-2xl border-2 backdrop-blur-3xl overflow-hidden origin-top"
          >
            <!-- Search Mode Toggle -->
          <div class="border-border/50 px-4 py-3">
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
                @click="handleSourceToggle(source.id)"
                :class="[
                  'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium',
                  store.selectedSources.includes(source.id)
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                ]"
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
                @click="handleWordlistSelect(wordlist)"
                :class="[
                  'w-full rounded-lg px-3 py-2 text-left text-sm font-medium transition-smooth',
                  store.selectedWordlist === wordlist
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                ]"
              >
                {{ wordlist }}
              </button>
            </div>
          </div>
          </div>
        </Transition>

        <!-- Search Results Dropdown -->
        <Transition
          enter-active-class="transition-all duration-300 ease-apple-bounce"
          leave-active-class="transition-all duration-300 ease-apple-bounce"
          enter-from-class="opacity-0 scale-95 translate-y-4"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-from-class="opacity-100 scale-100 translate-y-0"
          leave-to-class="opacity-0 scale-95 translate-y-4"
        >
          <div
            v-if="showSearchResults"
            class="dropdown-element border-border bg-background/20 cartoon-shadow-sm rounded-2xl border-2 backdrop-blur-3xl overflow-hidden origin-top"
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
              <span class="text-muted-foreground text-sm">Searching...</span>
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
              :class="[
                'flex w-full items-center justify-between px-4 py-3 text-left transition-smooth duration-150',
                'border-muted-foreground/50 active:scale-[0.98]',
                index === selectedIndex
                  ? 'bg-accent/60 scale-[1.02] border-l-6 pl-4'
                  : 'border-l-0 pl-4'
              ]"
              @click="selectResult(result)"
              @mouseenter="selectedIndex = index"
            >
              <span
                :class="[
                  'transition-smooth',
                  index === selectedIndex && 'text-primary font-semibold'
                ]"
              >
                {{ result.word }}
              </span>
              <div class="flex items-center gap-2 text-xs">
                <span
                  :class="[
                    'text-muted-foreground',
                    index === selectedIndex && 'text-primary font-semibold'
                  ]"
                >
                  {{ result.method }}
                </span>
                <span
                  :class="[
                    'text-muted-foreground',
                    index === selectedIndex && 'text-primary font-semibold'
                  ]"
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
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  ref,
  computed,
  onMounted,
  onUnmounted,
  nextTick,
  watch,
} from 'vue';
import { useScroll, useMagicKeys } from '@vueuse/core';
import { useAppStore } from '@/stores';
import type { SearchResult } from '@/types';
import Button from '@/components/ui/Button.vue';
import FancyF from '@/components/ui/icons/FancyF.vue';
import HamburgerIcon from '@/components/ui/icons/HamburgerIcon.vue';
import BouncyToggle from '@/components/ui/BouncyToggle.vue';
import { Sparkles, RefreshCw } from 'lucide-vue-next';
import WiktionaryIcon from '@/components/ui/icons/WiktionaryIcon.vue';
import OxfordIcon from '@/components/ui/icons/OxfordIcon.vue';
import DictionaryIcon from '@/components/ui/icons/DictionaryIcon.vue';

interface SearchBarProps {
  className?: string;
  shrinkPercentage?: number;
  hideDelay?: number;
  scrollThreshold?: number;
}

const props = withDefaults(defineProps<SearchBarProps>(), {
  shrinkPercentage: 0,
  hideDelay: 3000,
  scrollThreshold: 100,
});

const store = useAppStore();

// State
const query = ref(store.searchQuery || '');
const searchResults = ref<SearchResult[]>([]);
const isSearching = ref(false);
const selectedIndex = ref(0);
const aiSuggestions = ref<string[]>([]);
const isContainerHovered = ref(false);
const isFocused = ref(false);
const isShrunken = ref(false);
const regenerateRotation = ref(0);

// State machine for scroll/hover behavior
type SearchBarState = 'normal' | 'scrolled' | 'hovering' | 'focused';

const currentState = ref<SearchBarState>('normal');
const scrollProgress = ref(0); // 0-1 percentage of page height
const scrollInflectionPoint = ref(0.35); // 35% of page height
const documentHeight = ref(0);

// Refs
const searchInput = ref<HTMLInputElement>();
const searchContainer = ref<HTMLDivElement>();
const searchBarElement = ref<HTMLDivElement>();

// Timers
let searchTimer: ReturnType<typeof setTimeout> | undefined;
let scrollAnimationFrame: number | undefined;


// Scroll tracking
const { y: scrollY } = useScroll(window);

// Magic keys
const { escape } = useMagicKeys();

// Computed
const mode = computed(() => store.mode);
const placeholder = computed(() =>
  mode.value === 'dictionary'
    ? 'Enter a word to define...'
    : 'Enter a word to find synonyms...'
);

const showSearchResults = computed(() => {
  return isFocused.value && query.value.length > 0 && 
    (searchResults.value.length > 0 || isSearching.value || query.value.length < 2);
});

// State machine transitions
const transitionToState = (newState: SearchBarState) => {
  if (currentState.value === newState) return;
  
  currentState.value = newState;
  
  // Cancel any pending timers when state changes
  if (scrollAnimationFrame) {
    cancelAnimationFrame(scrollAnimationFrame);
    scrollAnimationFrame = undefined;
  }
};

// Debounced scroll update to prevent jittering
const updateScrollState = () => {
  if (scrollAnimationFrame) return;
  
  scrollAnimationFrame = requestAnimationFrame(() => {
    const maxScroll = Math.max(documentHeight.value - window.innerHeight, 1);
    scrollProgress.value = Math.min(scrollY.value / maxScroll, 1);
    
    // State machine logic - only transition states for icon visibility
    // The gradual shrinking happens continuously based on scrollProgress
    const shouldBeScrolled = scrollProgress.value >= scrollInflectionPoint.value;
    
    if (currentState.value === 'normal' && shouldBeScrolled) {
      transitionToState('scrolled');
    } else if (currentState.value === 'scrolled' && !shouldBeScrolled && !isContainerHovered.value) {
      transitionToState('normal');
    }
    
    scrollAnimationFrame = undefined;
  });
};


// Computed opacity for smooth icon fade-out
const iconOpacity = computed(() => {
  // Always full opacity when focused or hovered
  if (currentState.value === 'focused' || isContainerHovered.value) {
    return 1;
  }
  
  // Gradual fade based on scroll progress
  const progress = Math.min(scrollProgress.value / scrollInflectionPoint.value, 1);
  
  // Start fading at 30% of the way to inflection point, fully hidden at 70%
  const fadeStart = 0.3;
  const fadeEnd = 0.7;
  
  if (progress <= fadeStart) {
    return 1; // Full opacity
  } else if (progress >= fadeEnd) {
    return 0; // Fully hidden
  } else {
    // Linear interpolation between fadeStart and fadeEnd
    const fadeProgress = (progress - fadeStart) / (fadeEnd - fadeStart);
    return 1 - fadeProgress;
  }
});


// Smooth style transitions based on state
const containerStyle = computed(() => {
  const progress = Math.min(scrollProgress.value / scrollInflectionPoint.value, 1);
  
  // Don't shrink if controls or search results are shown, or when focused/hovered
  if (currentState.value === 'focused' || isContainerHovered.value || store.showControls || showSearchResults.value) {
    return {
      maxWidth: '24rem',
      transform: 'scale(1)',
      opacity: '1',
      transition: 'all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)'
    };
  }
  
  // Gradual interpolation based on scroll progress (0% to 35%)
  const baseWidth = 24 - (progress * 6); // 24rem -> 18rem at 35%
  const scale = 1 - (progress * 0.15); // 1 -> 0.85 at 35%
  const opacity = 1 - (progress * 0.1); // 1 -> 0.9 at 35%
  
  return {
    maxWidth: `${baseWidth}rem`,
    transform: `scale(${scale})`,
    opacity: opacity.toString(),
    transition: progress > 0 ? 'all 0.1s cubic-bezier(0.25, 0.46, 0.45, 0.94)' : 'all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)'
  };
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


// Initialize document height for timeline calculations
const initializeDocumentHeight = () => {
  documentHeight.value = Math.max(
    document.body.scrollHeight,
    document.body.offsetHeight,
    document.documentElement.clientHeight,
    document.documentElement.scrollHeight,
    document.documentElement.offsetHeight
  );
};

// Simple hover management (no timers)
const handleMouseEnter = () => {
  isContainerHovered.value = true;
  
  // Transition to hovering state
  if (currentState.value === 'scrolled') {
    transitionToState('hovering');
  }
};

const handleMouseLeave = () => {
  isContainerHovered.value = false;
  
  // Only transition back if not focused
  if (currentState.value === 'hovering' && !isFocused.value) {
    transitionToState('scrolled');
  }
};

const handleFocus = () => {
  isFocused.value = true;
  
  // Transition to focused state
  transitionToState('focused');

  if (store.sessionState?.searchResults?.length > 0 && query.value.length >= 2) {
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
  isFocused.value = false;
  
  // Transition back to appropriate state based on scroll position
  const shouldBeScrolled = scrollProgress.value >= scrollInflectionPoint.value;
  transitionToState(shouldBeScrolled ? 'scrolled' : 'normal');
};

const handleInput = (event: Event) => {
  const input = event.target as HTMLInputElement;
  store.searchCursorPosition = input.selectionStart || 0;
  performSearch();
};

const handleEscape = () => {
  const hasSearchResults = showSearchResults.value;
  
  if (hasSearchResults && store.showControls) {
    // Both shown: hide controls first
    store.showControls = false;
  } else if (store.showControls) {
    // Only controls shown: hide them
    store.showControls = false;
  } else if (hasSearchResults) {
    // Only search results shown: clear them
    query.value = '';
    searchResults.value = [];
    isSearching.value = false;
  } else {
    // Nothing shown: blur input
    searchInput.value?.blur();
  }
};

// Watch for escape key
watch(escape, (pressed) => {
  if (pressed) {
    handleEscape();
  }
});

const performSearch = () => {
  clearTimeout(searchTimer);
  store.searchQuery = query.value;

  if (!query.value) {
    searchResults.value = [];
    isSearching.value = false;
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
  if (searchResults.value.length === 0) return;

  selectedIndex.value = Math.max(
    0,
    Math.min(searchResults.value.length - 1, selectedIndex.value + direction)
  );

  store.searchSelectedIndex = selectedIndex.value;
};

const handleHamburgerClick = () => {
  store.toggleControls();
  // Restore focus to search input after toggling controls
  nextTick(() => {
    searchInput.value?.focus();
  });
};

const handleForceRegenerate = () => {
  // Toggle force refresh mode
  store.forceRefreshMode = !store.forceRefreshMode;
  
  // Add rotation on toggle
  regenerateRotation.value += 360;
  
  // Restore focus to search input after toggling
  nextTick(() => {
    searchInput.value?.focus();
  });
};

const handleSourceToggle = (sourceId: string) => {
  store.toggleSource(sourceId);
  // Restore focus to search input after toggling source
  nextTick(() => {
    searchInput.value?.focus();
  });
};

const handleWordlistSelect = (wordlist: string) => {
  store.setWordlist(wordlist);
  // Restore focus to search input after selecting wordlist
  nextTick(() => {
    searchInput.value?.focus();
  });
};

const handleModeToggle = () => {
  store.toggleMode();
  // Restore focus to search input after toggling mode
  nextTick(() => {
    searchInput.value?.focus();
  });
};

// Click outside handler
const handleClickOutside = (event: Event) => {
  const target = event.target as Element;

  if (!target.closest('.search-container')) {
    store.showControls = false;
    searchResults.value = [];
    isSearching.value = false;
  }
};

// Smooth scroll handling with debouncing
watch(scrollY, () => {
  // Use debounced update to prevent jittering
  updateScrollState();
});

// Legacy shrink state handling (enhanced with state machine)
watch([() => props.shrinkPercentage, isContainerHovered], ([shrinkPct, hovered]) => {
  if (shrinkPct > 0 && !hovered) {
    isShrunken.value = true;
    // Force scrolled state for external shrink requests
    transitionToState('scrolled');
  } else if (shrinkPct === 0) {
    isShrunken.value = false;
    // Reset to appropriate state based on scroll position
    const shouldBeScrolled = scrollProgress.value >= scrollInflectionPoint.value;
    transitionToState(shouldBeScrolled ? 'scrolled' : 'normal');
  }
});

// Mounted
onMounted(async () => {
  // Reset controls state on mount
  store.showControls = false;
  
  // Initialize document height for timeline calculations
  initializeDocumentHeight();
  
  // Update on window resize
  window.addEventListener('resize', initializeDocumentHeight);
  
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
  if (scrollAnimationFrame) {
    cancelAnimationFrame(scrollAnimationFrame);
  }
  document.removeEventListener('click', handleClickOutside);
  window.removeEventListener('resize', initializeDocumentHeight);
});
</script>

<style scoped>
/* Removed will-change to fix blur issues */

/* Disable animations for reduced motion */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}
</style>