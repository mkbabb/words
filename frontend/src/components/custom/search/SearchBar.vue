<template>
  <div
    ref="searchContainer"
    :class="[
      'search-container relative z-50 origin-top',
      'w-full max-w-60 sm:max-w-xs md:max-w-md lg:max-w-4xl',
      'mx-auto',
      props.className
    ]"
    :style="containerStyle"
    @mouseenter="handleMouseEnterWrapper"
    @mouseleave="handleMouseLeaveWrapper"
  >
    <!-- Main Layout -->
    <div class="pointer-events-auto relative">
      <!-- Search Bar -->
      <div
        ref="searchBarElement"
        :class="[
          'search-bar flex items-center gap-2 p-2 h-16',
          'border-border bg-background/20 border-2 backdrop-blur-3xl',
          'cartoon-shadow-sm rounded-2xl transition-all duration-200 ease-out',
          {
            'cartoon-shadow-sm-hover': isContainerHovered,
            'bg-background/30': isContainerHovered
          }
        ]"
      >
        <!-- Mode Toggle - Fixed to left edge -->
        <div
          :class="[
            'flex items-center justify-center overflow-hidden transition-all duration-300 ease-out flex-shrink-0'
          ]"
          :style="{ 
            opacity: iconOpacity,
            transform: `scale(${0.9 + iconOpacity * 0.1})`,
            pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
            width: iconOpacity > 0.1 ? '48px' : '0px',
            marginRight: iconOpacity > 0.1 ? '8px' : '0px'
          }"
        >
          <FancyF
            :mode="mode"
            size="lg"
            clickable
            @toggle-mode="handleModeToggle"
          />
        </div>

        <!-- Search Input Container with Autocomplete - Maximum space -->
        <div class="relative flex-1 min-w-0 flex-grow max-w-none">
          <!-- Autocomplete Preview Text -->
          <div
            v-if="autocompleteText"
            :class="[
              'absolute left-0 top-0 h-12 flex items-center pointer-events-none text-base transition-all duration-300 ease-out',
              'text-muted-foreground/50'
            ]"
            :style="{
              paddingLeft: iconOpacity > 0.1 ? '1rem' : '1.5rem',
              paddingRight: iconOpacity > 0.1 ? '1rem' : '1.5rem',
              textAlign: iconOpacity < 0.3 ? 'center' : 'left'
            }"
          >
            <span class="invisible">{{ query }}</span><span>{{ autocompleteText.slice(query.length) }}</span>
          </div>
          
          <!-- Main Search Input -->
          <input
            ref="searchInput"
            v-model="query"
            :placeholder="placeholder"
            :class="[
              'placeholder:text-muted-foreground focus:ring-primary h-12 w-full rounded-xl bg-transparent py-2 text-base outline-none focus:ring-1 text-ellipsis overflow-hidden whitespace-nowrap transition-all duration-300 ease-out relative z-10'
            ]"
            :style="{
              paddingLeft: iconOpacity > 0.1 ? '1rem' : '1.5rem',
              paddingRight: iconOpacity > 0.1 ? '1rem' : '1.5rem',
              textAlign: iconOpacity < 0.3 ? 'center' : 'left'
            }"
            @keydown.enter="handleEnter"
            @keydown.tab.prevent="handleAutocompleteAccept"
            @keydown.space="handleSpaceKey"
            @keydown.down.prevent="navigateResults(1)"
            @keydown.up.prevent="navigateResults(-1)"
            @keydown.left="handleArrowKey"
            @keydown.right="handleArrowKey"
            @keydown.escape="handleEscape"
            @focus="handleFocusWrapper"
            @blur="handleBlurWrapper"
            @input="handleInput"
            @click="handleInputClick"
          />
        </div>

        <!-- Regenerate Button - Same size as hamburger -->
        <div
          v-if="store.currentEntry && store.searchMode === 'lookup'"
          :class="[
            'flex items-center justify-center overflow-hidden transition-all duration-300 ease-out flex-shrink-0'
          ]"
          :style="{ 
            opacity: iconOpacity,
            transform: `scale(${0.9 + iconOpacity * 0.1})`,
            pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
            width: iconOpacity > 0.1 ? '48px' : '0px',
            marginLeft: iconOpacity > 0.1 ? '8px' : '0px'
          }"
        >
          <button
            @click="handleForceRegenerate"
            @mouseenter="handleRegenerateHover"
            @mouseleave="handleRegenerateLeave"
            :class="[
              'flex h-12 w-12 items-center justify-center rounded-lg',
              store.forceRefreshMode ? 'bg-primary/20 text-primary' : '',
              'hover:bg-muted/50 transition-all duration-200 ease-out'
            ]"
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

        <!-- Hamburger Button - Always visible -->
        <div
          :class="[
            'overflow-hidden transition-all duration-300 ease-out flex-shrink-0'
          ]"
          :style="{ 
            opacity: iconOpacity,
            transform: `scale(${0.9 + iconOpacity * 0.1})`,
            pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
            width: iconOpacity > 0.1 ? '48px' : '0px',
            marginLeft: iconOpacity > 0.1 ? '8px' : '0px'
          }"
        >
          <HamburgerIcon
            :is-open="showControls"
            @toggle="handleHamburgerClick"
          />
        </div>


        <!-- Progress Bar -->
        <div
          v-if="store.loadingProgress > 0"
          class="absolute right-0 -bottom-2 left-0 h-2 overflow-hidden"
        >
          <div
            class="h-full rounded-full transition-[width] duration-300"
            :style="{ 
              width: `${store.loadingProgress}%`,
              background: rainbowGradient
            }"
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
            v-if="showControls"
            ref="controlsDropdown"
            class="dropdown-element border-border bg-background/20 cartoon-shadow-sm mb-2 rounded-2xl border-2 backdrop-blur-3xl overflow-hidden origin-top"
            @mousedown.prevent
            @click="handleSearchAreaInteraction"
          >
            <!-- Search Mode Toggle -->
          <div class="border-border/50 px-4 py-3">
            <h3 class="mb-3 text-sm font-medium">Mode</h3>
            <BouncyToggle
              v-model="store.searchMode"
              :options="[
                { label: 'Lookup', value: 'lookup' },
                { label: 'Wordlist', value: 'wordlist' },
                { label: 'Stage', value: 'stage' },
              ]"
            />
          </div>

          <!-- Sources (Lookup Mode) -->
          <div
            v-if="store.searchMode === 'lookup'"
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
            v-if="store.searchMode === 'lookup' && aiSuggestions.length > 0"
            class="border-border/50 border-t px-4 py-3"
          >
            <div class="flex items-center gap-2 overflow-hidden">
              <Sparkles class="text-muted-foreground flex-shrink-0" :size="16" />
              <div class="flex items-center gap-2 overflow-hidden flex-1 min-w-0">
                <Button
                  v-for="word in aiSuggestions"
                  :key="word"
                  variant="outline"
                  size="sm"
                  class="hover-text-grow text-xs flex-shrink-0 whitespace-nowrap"
                  @click="selectWord(word)"
                >
                  {{ word }}
                </Button>
              </div>
            </div>
          </div>

          </div>
        </Transition>

        <!-- Search Results Container with coordinated positioning -->
        <div :style="resultsContainerStyle">
          <Transition
            enter-active-class="transition-all duration-300 ease-apple-bounce"
            leave-active-class="transition-all duration-250 ease-out"
            enter-from-class="opacity-0 scale-95 translate-y-4"
            enter-to-class="opacity-100 scale-100 translate-y-0"
            leave-from-class="opacity-100 scale-100 translate-y-0"
            leave-to-class="opacity-0 scale-95 translate-y-4"
          >
            <div
              v-if="showResults"
              ref="searchResultsDropdown"
              class="dropdown-element border-border bg-background/20 cartoon-shadow-sm rounded-2xl border-2 backdrop-blur-3xl overflow-hidden origin-top"
              @mousedown.prevent
              @click="handleSearchAreaInteraction"
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
            ref="searchResultsContainer"
            class="bg-background/20 max-h-64 overflow-y-auto backdrop-blur-3xl"
          >
            <button
              v-for="(result, index) in searchResults"
              :key="result.word"
              :ref="el => { if (el) resultRefs[index] = el as HTMLButtonElement }"
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
  reactive,
} from 'vue';
import { useScroll, useMagicKeys } from '@vueuse/core';
import { useAppStore } from '@/stores';
import type { SearchResult } from '@/types';
import { Button } from '@/components/ui';
import { FancyF, HamburgerIcon } from '@/components/custom/icons';
import { BouncyToggle } from '@/components/custom/animation';
import { Sparkles, RefreshCw } from 'lucide-vue-next';
import { WiktionaryIcon, OxfordIcon, DictionaryIcon } from '@/components/custom/icons';
import { generateRainbowGradient } from '@/utils/animations';

interface SearchBarProps {
  className?: string;
  shrinkPercentage?: number;
  hideDelay?: number;
  scrollThreshold?: number;
}

// Define emits
const emit = defineEmits<{
  focus: [];
  blur: [];
  mouseenter: [];
  mouseleave: [];
  'stage-enter': [query: string];
}>();

const props = withDefaults(defineProps<SearchBarProps>(), {
  shrinkPercentage: 0,
  hideDelay: 3000,
  scrollThreshold: 100,
});

const store = useAppStore();

// State
const query = ref(store.searchQuery || '');
const autocompleteText = ref('');
const searchResults = ref<SearchResult[]>([]);
const isSearching = ref(false);
const selectedIndex = ref(0);
const aiSuggestions = ref<string[]>([]);
const isContainerHovered = ref(false);
const isFocused = ref(false);
const isShrunken = ref(false);
const regenerateRotation = ref(0);

// Enhanced dropdown state management
const showControls = ref(false);
const showResults = ref(false);
const isInteractingWithSearchArea = ref(false);

// State machine for scroll/hover behavior
type SearchBarState = 'normal' | 'scrolled' | 'hovering' | 'focused';

const currentState = ref<SearchBarState>('normal');
const scrollProgress = ref(0); // 0-1 percentage of page height
const scrollInflectionPoint = ref(0.35); // 35% of page height
const documentHeight = ref(0);

// Scroll momentum tracking to prevent bouncing
const lastScrollY = ref(0);
const scrollVelocity = ref(0);
const scrollDirection = ref(0); // 1 for down, -1 for up, 0 for static
const momentumThreshold = ref(8); // Lower threshold for more sensitive detection
const velocityHistory = ref<number[]>([]); // Track velocity over time
const isInMomentum = ref(false); // Track if we're currently in momentum scrolling
let velocityTimer: ReturnType<typeof setTimeout> | undefined;
let momentumCooldown: ReturnType<typeof setTimeout> | undefined;

// Refs
const searchInput = ref<HTMLInputElement>();
const searchResultsContainer = ref<HTMLDivElement>();
const resultRefs = reactive<(HTMLButtonElement | null)[]>([]);
const searchContainer = ref<HTMLDivElement>();
const searchBarElement = ref<HTMLDivElement>();
const controlsDropdown = ref<HTMLDivElement>();
const searchResultsDropdown = ref<HTMLDivElement>();

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
const rainbowGradient = computed(() => generateRainbowGradient(8));

// Enhanced computed properties for coordinated dropdown management
const shouldShowResults = computed(() => {
  return isFocused.value && query.value.length > 0 && 
    (searchResults.value.length > 0 || isSearching.value || query.value.length >= 2);
});

// Dynamic positioning: results move down when controls are shown
const resultsContainerStyle = computed(() => {
  return {
    paddingTop: showControls.value ? '8px' : '0px',
    transition: 'all 300ms cubic-bezier(0.25, 0.1, 0.25, 1)'
  };
});



// Sync reactive state with computed
watch(shouldShowResults, (newVal) => {
  showResults.value = newVal;
});

watch(() => store.showControls, (newVal) => {
  showControls.value = newVal;
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

// Advanced scroll update with momentum smoothing and hysteresis
const updateScrollState = () => {
  if (scrollAnimationFrame) return;
  
  scrollAnimationFrame = requestAnimationFrame(() => {
    // Calculate scroll velocity and direction
    const currentScrollY = scrollY.value;
    const deltaY = currentScrollY - lastScrollY.value;
    const currentVelocity = Math.abs(deltaY);
    
    // Track scroll direction
    if (Math.abs(deltaY) > 1) {
      scrollDirection.value = deltaY > 0 ? 1 : -1;
    }
    
    // Update velocity history (keep last 5 frames)
    velocityHistory.value.push(currentVelocity);
    if (velocityHistory.value.length > 5) {
      velocityHistory.value.shift();
    }
    
    // Calculate average velocity for smoother detection
    const avgVelocity = velocityHistory.value.reduce((sum, v) => sum + v, 0) / velocityHistory.value.length;
    scrollVelocity.value = avgVelocity;
    lastScrollY.value = currentScrollY;
    
    // Detect momentum scrolling with hysteresis
    const wasInMomentum = isInMomentum.value;
    if (!wasInMomentum && avgVelocity > momentumThreshold.value) {
      isInMomentum.value = true;
    } else if (wasInMomentum && avgVelocity < momentumThreshold.value * 0.5) {
      // Use lower threshold to exit momentum (hysteresis)
      isInMomentum.value = false;
    }
    
    // Reset momentum state after scrolling stops completely
    clearTimeout(velocityTimer);
    clearTimeout(momentumCooldown);
    
    velocityTimer = setTimeout(() => {
      scrollVelocity.value = 0;
      velocityHistory.value = [];
    }, 100);
    
    // Add cooldown period after momentum ends
    if (!isInMomentum.value && wasInMomentum) {
      momentumCooldown = setTimeout(() => {
        // Allow state changes again after momentum completely stops
      }, 200);
    }
    
    const maxScroll = Math.max(documentHeight.value - window.innerHeight, 1);
    scrollProgress.value = Math.min(scrollY.value / maxScroll, 1);
    
    // State machine with momentum awareness and hysteresis
    const isHighMomentum = isInMomentum.value || avgVelocity > momentumThreshold.value;
    
    // Add hysteresis: require more significant change to switch states
    const hysteresisBuffer = 0.05; // 5% buffer zone
    let shouldTransition = false;
    
    if (currentState.value === 'normal') {
      shouldTransition = scrollProgress.value >= scrollInflectionPoint.value + hysteresisBuffer;
    } else if (currentState.value === 'scrolled') {
      shouldTransition = scrollProgress.value <= scrollInflectionPoint.value - hysteresisBuffer;
    }
    
    // Only allow state changes when not in high momentum and with hysteresis
    if (!isHighMomentum) {
      if (currentState.value === 'normal' && shouldTransition) {
        transitionToState('scrolled');
      } else if (currentState.value === 'scrolled' && shouldTransition && !isContainerHovered.value) {
        transitionToState('normal');
      }
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


// Smooth style transitions with optimized max-width for mobile and desktop
const containerStyle = computed(() => {
  const progress = Math.min(scrollProgress.value / scrollInflectionPoint.value, 1);
  
  // Use CSS clamp for responsive width
  const responsiveMaxWidth = 'min(40rem, calc(100vw - 2rem))';
  
  // Focused/hovered states: full size but responsive
  if (currentState.value === 'focused' || isContainerHovered.value) {
    return {
      maxWidth: responsiveMaxWidth,
      transform: 'scale(1)',
      opacity: '1',
      transition: 'all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)'
    };
  }
  
  // Controls/results shown: prevent shrinking but responsive
  if (showControls.value || showResults.value) {
    return {
      maxWidth: responsiveMaxWidth,
      transform: 'scale(1)',
      opacity: '1',
      transition: 'all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)'
    };
  }
  
  // Scroll-based shrinking with responsive bounds
  const clampedProgress = Math.max(0, Math.min(progress, 1));
  const scale = Math.max(0.85, 1 - (clampedProgress * 0.15)); // Bounded: 1 -> 0.85
  const opacity = Math.max(0.9, 1 - (clampedProgress * 0.1)); // Bounded: 1 -> 0.9
  
  // Shrink max-width more aggressively on scroll
  const minWidth = 'min(32rem, calc(100vw - 4rem))';
  
  return {
    maxWidth: clampedProgress > 0.5 ? minWidth : responsiveMaxWidth,
    transform: `scale(${scale})`,
    opacity: opacity.toString(),
    transition: clampedProgress > 0 ? 'all 0.1s cubic-bezier(0.25, 0.46, 0.45, 0.94)' : 'all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)'
  };
});

// Sources configuration
const sources = [
  { id: 'wiktionary', name: 'Wiktionary', icon: WiktionaryIcon },
  { id: 'oxford', name: 'Oxford', icon: OxfordIcon },
  { id: 'dictionary_com', name: 'Dictionary.com', icon: DictionaryIcon },
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

// Simple hover management (no timers) with emit
const handleMouseEnterWrapper = () => {
  handleMouseEnter();
  emit('mouseenter');
};

const handleMouseLeaveWrapper = () => {
  handleMouseLeave();
  emit('mouseleave');
};

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

const handleFocusWrapper = () => {
  handleFocus();
  emit('focus');
};

const handleBlurWrapper = () => {
  handleBlur();
  emit('blur');
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
  setTimeout(() => {
    if (isInteractingWithSearchArea.value) return;
    
    isFocused.value = false;
    
    // Only hide results if not interacting with search area
    if (!showControls.value) {
      showResults.value = false;
      searchResults.value = [];
      isSearching.value = false;
    }
    
    // Transition back to appropriate state based on scroll position
    const shouldBeScrolled = scrollProgress.value >= scrollInflectionPoint.value;
    transitionToState(shouldBeScrolled ? 'scrolled' : 'normal');
  }, 150);
};

const handleInput = (event: Event) => {
  const input = event.target as HTMLInputElement;
  store.searchCursorPosition = input.selectionStart || 0;
  performSearch();
};

// Unified close handler
const handleClose = () => {
  if (showControls.value && showResults.value) {
    // Both shown: hide both
    store.showControls = false;
    showResults.value = false;
    searchResults.value = [];
    isSearching.value = false;
  } else if (showControls.value) {
    // Only controls shown: hide controls
    store.showControls = false;
  } else if (showResults.value) {
    // Only results shown: hide results
    showResults.value = false;
    searchResults.value = [];
    isSearching.value = false;
  }
};

const handleEscape = () => {
  if (showControls.value || showResults.value) {
    handleClose();
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

  // If autocomplete is available, accept it
  if (autocompleteText.value) {
    await handleAutocompleteAccept();
    return;
  }

  // Handle stage mode - run mock pipeline instead of definition lookup
  if (store.searchMode === 'stage' && query.value) {
    store.searchQuery = query.value;
    // Emit event to trigger mock pipeline in stage controls
    emit('stage-enter', query.value);
    // Blur the input after stage mode enter
    nextTick(() => {
      searchInput.value?.blur();
    });
    return;
  }

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
  // Don't immediately lose focus, let the natural blur handle it
  searchResults.value = [];
  store.hasSearched = true;
  await store.getDefinition(result.word);
  // Blur the input after selection
  nextTick(() => {
    searchInput.value?.blur();
  });
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

  // Scroll selected item into view
  nextTick(() => {
    const selectedElement = resultRefs[selectedIndex.value];
    if (selectedElement && searchResultsContainer.value) {
      selectedElement.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest'
      });
    }
  });
};

// Enhanced interaction handlers
const handleSearchAreaInteraction = () => {
  isInteractingWithSearchArea.value = true;
  setTimeout(() => {
    isInteractingWithSearchArea.value = false;
  }, 100);
};

const handleHamburgerClick = () => {
  store.toggleControls();
  handleSearchAreaInteraction();
  // Restore focus to search input after toggling controls
  nextTick(() => {
    searchInput.value?.focus();
  });
};

// iOS-style regenerate button handlers
const handleRegenerateHover = () => {
  // Gentle rotation on hover (like iOS)
  regenerateRotation.value += 180;
};

const handleRegenerateLeave = () => {
  // Return to original position
  regenerateRotation.value -= 180;
};

const handleForceRegenerate = () => {
  handleSearchAreaInteraction();
  
  // Toggle force refresh mode
  store.forceRefreshMode = !store.forceRefreshMode;
  
  // Full iOS-style rotation on click (360° + current)
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


const handleModeToggle = () => {
  store.toggleMode();
  // Do not modify focus state when toggling mode
};

// Autocomplete logic
const updateAutocomplete = () => {
  if (!query.value || query.value.length < 2 || !searchResults.value.length) {
    autocompleteText.value = '';
    return;
  }

  // Take the top match (highest score)
  const topMatch = searchResults.value[0];
  
  // Check if the top match starts with the current query (case insensitive)
  const queryLower = query.value.toLowerCase();
  const wordLower = topMatch.word.toLowerCase();
  
  if (wordLower.startsWith(queryLower) && topMatch.word.length > query.value.length) {
    // Use the top match for completion
    autocompleteText.value = topMatch.word;
  } else {
    // No suitable completion available
    autocompleteText.value = '';
  }
};

const handleAutocompleteAccept = async () => {
  if (autocompleteText.value) {
    query.value = autocompleteText.value;
    store.searchQuery = autocompleteText.value;
    isFocused.value = false;
    searchResults.value = [];
    store.hasSearched = true;
    autocompleteText.value = '';
    await store.getDefinition(query.value);
  }
};

const fillAutocomplete = () => {
  if (autocompleteText.value) {
    query.value = autocompleteText.value;
    store.searchQuery = autocompleteText.value;
    autocompleteText.value = '';
    // Move cursor to end
    nextTick(() => {
      if (searchInput.value) {
        searchInput.value.setSelectionRange(query.value.length, query.value.length);
      }
    });
  }
};

const handleSpaceKey = (event: KeyboardEvent) => {
  if (autocompleteText.value) {
    event.preventDefault();
    fillAutocomplete();
    // Add the space after filling
    nextTick(() => {
      query.value += ' ';
      store.searchQuery = query.value;
    });
  }
};

const handleInputClick = (_event: MouseEvent) => {
  handleSearchAreaInteraction();
  
  if (autocompleteText.value && searchInput.value) {
    const input = searchInput.value;
    const cursorPosition = input.selectionStart || 0;
    
    // If cursor is positioned beyond the current query length (in ghost text area)
    if (cursorPosition > query.value.length) {
      fillAutocomplete();
    }
  }
};

const handleArrowKey = (event: KeyboardEvent) => {
  if (autocompleteText.value && searchInput.value) {
    const currentPosition = searchInput.value.selectionStart || 0;
    
    // If it's a right arrow and we're at the end of the current text
    if (event.key === 'ArrowRight' && currentPosition === query.value.length) {
      event.preventDefault();
      fillAutocomplete();
      return;
    }
    
    // Use nextTick to get the cursor position after the arrow key press for other cases
    nextTick(() => {
      if (searchInput.value) {
        const cursorPosition = searchInput.value.selectionStart || 0;
        
        // If cursor moves beyond the current query length (into ghost text area)
        if (cursorPosition > query.value.length) {
          fillAutocomplete();
        }
      }
    });
  }
};

// Click outside handler
const handleClickOutside = (event: Event) => {
  if (isInteractingWithSearchArea.value) return;
  
  const target = event.target as Element;
  if (!target.closest('.search-container')) {
    handleClose();
  }
};

// Smooth scroll handling with debouncing
watch(scrollY, () => {
  // Use debounced update to prevent jittering
  updateScrollState();
});

// Watchers for autocomplete
watch(searchResults, () => {
  selectedIndex.value = 0;
  store.searchSelectedIndex = 0;
  updateAutocomplete();
});

watch(query, () => {
  updateAutocomplete();
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
  clearTimeout(velocityTimer);
  clearTimeout(momentumCooldown);
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