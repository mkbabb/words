<template>
    <div
        ref="searchContainer"
        :class="[
            'search-container relative z-50 origin-top',
            'w-full',
            'mx-auto',
            props.className,
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
                    'search-bar flex h-16 items-center gap-2 p-1',
                    'border-2 border-border bg-background/20 backdrop-blur-3xl',
                    'cartoon-shadow-sm rounded-2xl transition-all duration-200 ease-out',
                    {
                        'cartoon-shadow-sm-hover': isContainerHovered,
                        'bg-background/30': isContainerHovered,
                    },
                ]"
            >
                <!-- Mode Toggle - Fixed to left edge -->
                <div
                    :class="[
                        'flex flex-shrink-0 items-center justify-center overflow-hidden transition-all duration-300 ease-out',
                    ]"
                    :style="{
                        opacity: iconOpacity,
                        transform: `scale(${0.9 + iconOpacity * 0.1})`,
                        pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
                        width: iconOpacity > 0.1 ? '48px' : '0px',
                        marginRight: iconOpacity > 0.1 ? '2px' : '0px',
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
                <div class="relative max-w-none min-w-0 flex-1 flex-grow">
                    <!-- Autocomplete Preview Text -->
                    <div
                        v-if="autocompleteText"
                        :class="[
                            'pointer-events-none absolute top-0 left-0 flex h-12 items-center text-lg transition-all duration-300 ease-out',
                            'text-muted-foreground/50',
                        ]"
                        :style="{
                            paddingLeft: iconOpacity > 0.1 ? '1rem' : '1.5rem',
                            paddingRight: iconOpacity > 0.1 ? '1rem' : '1.5rem',
                            textAlign: iconOpacity < 0.3 ? 'center' : 'left',
                        }"
                    >
                        <span class="invisible">{{ query }}</span
                        ><span>{{ autocompleteText.slice(query.length) }}</span>
                    </div>

                    <!-- Main Search Input -->
                    <input
                        ref="searchInput"
                        v-model="query"
                        :placeholder="placeholder"
                        :class="[
                            'relative z-10 h-12 w-full overflow-hidden rounded-xl bg-transparent py-2 text-lg text-ellipsis whitespace-nowrap transition-all duration-300 ease-out outline-none placeholder:text-muted-foreground',
                            'focus:ring-1 focus:ring-gray-300 dark:focus:ring-gray-600',
                        ]"
                        :style="{
                            paddingLeft: iconOpacity > 0.1 ? '1rem' : '1.5rem',
                            paddingRight: iconOpacity > 0.1 ? '1rem' : '1.5rem',
                            textAlign: iconOpacity < 0.3 ? 'center' : 'left',
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
                        'flex flex-shrink-0 items-center justify-center overflow-hidden transition-all duration-300 ease-out',
                    ]"
                    :style="{
                        opacity: iconOpacity,
                        transform: `scale(${0.9 + iconOpacity * 0.1})`,
                        pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
                        width: iconOpacity > 0.1 ? '48px' : '0px',
                        marginLeft: iconOpacity > 0.1 ? '8px' : '0px',
                    }"
                >
                    <button
                        @click="handleForceRegenerate"
                        @mouseenter="handleRegenerateHover"
                        @mouseleave="handleRegenerateLeave"
                        :class="[
                            'flex h-12 w-12 items-center justify-center rounded-lg',
                            store.forceRefreshMode
                                ? 'bg-primary/20 text-primary'
                                : '',
                            'transition-all duration-200 ease-out hover:bg-muted/50',
                        ]"
                        :title="
                            store.forceRefreshMode
                                ? 'Force refresh mode ON - Next lookup will regenerate'
                                : 'Toggle force refresh mode'
                        "
                    >
                        <RefreshCw
                            :size="20"
                            :style="{
                                transform: `rotate(${regenerateRotation}deg)`,
                                transition:
                                    'transform 700ms cubic-bezier(0.175, 0.885, 0.32, 1.4)',
                            }"
                        />
                    </button>
                </div>

                <!-- Debug: Clear Storage Button -->
                <div
                    v-if="isDevelopment"
                    :class="[
                        'flex-shrink-0 overflow-hidden transition-all duration-300 ease-out',
                    ]"
                    :style="{
                        opacity: iconOpacity,
                        transform: `scale(${0.9 + iconOpacity * 0.1})`,
                        pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
                        width: iconOpacity > 0.1 ? '48px' : '0px',
                        marginLeft: iconOpacity > 0.1 ? '8px' : '0px',
                    }"
                >
                    <button
                        @click="clearAllStorage"
                        class="flex h-12 w-12 items-center justify-center rounded-lg bg-red-500/10 text-red-500 transition-all duration-200 ease-out hover:bg-red-500/20"
                        title="Clear all local storage (DEBUG)"
                    >
                        <Trash2 :size="20" />
                    </button>
                </div>

                <!-- Hamburger Button - Always visible -->
                <div
                    :class="[
                        'flex-shrink-0 overflow-hidden transition-all duration-300 ease-out',
                    ]"
                    :style="{
                        opacity: iconOpacity,
                        transform: `scale(${0.9 + iconOpacity * 0.1})`,
                        pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
                        width: iconOpacity > 0.1 ? '48px' : '0px',
                        marginLeft: iconOpacity > 0.1 ? '8px' : '0px',
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
                    class="absolute right-0 -bottom-2 left-0 h-2
                        overflow-hidden"
                >
                    <div
                        class="h-full rounded-full transition-[width]
                            duration-300"
                        :style="{
                            width: `${store.loadingProgress}%`,
                            background: rainbowGradient,
                        }"
                    />
                </div>
            </div>

            <!-- Dropdowns Container - Absolutely positioned to prevent content shifting -->
            <div class="absolute top-full right-0 left-0 z-50 pt-2">
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
                        class="dropdown-element cartoon-shadow-sm mb-2
                            origin-top overflow-hidden rounded-2xl border-2
                            border-border bg-background/20 backdrop-blur-3xl"
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
                            class="border-t border-border/50 px-4 py-3"
                        >
                            <h3 class="mb-3 text-sm font-medium">Sources</h3>
                            <div class="flex flex-wrap gap-2">
                                <button
                                    v-for="source in sources"
                                    :key="source.id"
                                    @click="handleSourceToggle(source.id)"
                                    :class="[
                                        'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium',
                                        store.selectedSources.includes(
                                            source.id
                                        )
                                            ? 'bg-primary text-primary-foreground shadow-sm'
                                            : 'bg-muted text-muted-foreground hover:bg-muted/80',
                                    ]"
                                >
                                    <component :is="source.icon" :size="16" />
                                    {{ source.name }}
                                </button>
                            </div>
                        </div>

                        <!-- Languages (Lookup Mode) -->
                        <div
                            v-if="store.searchMode === 'lookup'"
                            class="border-t border-border/50 px-4 py-3"
                        >
                            <h3 class="mb-3 text-sm font-medium">Languages</h3>
                            <div class="flex flex-wrap gap-2">
                                <button
                                    v-for="language in languages"
                                    :key="language.value"
                                    @click="handleLanguageToggle(language.value)"
                                    :class="[
                                        'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium',
                                        store.selectedLanguages.includes(
                                            language.value
                                        )
                                            ? 'bg-primary text-primary-foreground shadow-sm'
                                            : 'bg-muted text-muted-foreground hover:bg-muted/80',
                                    ]"
                                >
                                    <component :is="language.icon" :size="16" />
                                    {{ language.label }}
                                </button>
                            </div>
                        </div>

                        <!-- AI Suggestions -->
                        <div
                            v-if="
                                store.searchMode === 'lookup' &&
                                aiSuggestions.length > 0
                            "
                            class="border-t border-border/50 px-4 py-3"
                        >
                            <div class="flex flex-col items-center gap-3">
                                <div
                                    class="flex flex-wrap items-center
                                        justify-center gap-2"
                                >
                                    <Button
                                        v-for="word in aiSuggestions"
                                        :key="word"
                                        variant="outline"
                                        size="default"
                                        class="hover-text-grow flex-shrink-0
                                            text-sm whitespace-nowrap font-medium"
                                        @click="selectWord(word)"
                                    >
                                        {{ word }}
                                    </Button>
                                </div>
                            </div>
                        </div>
                    </div>
                </Transition>

                <!-- Search Results Container - positioned below controls when both visible -->
                <div
                    :style="resultsContainerStyle"
                    :class="{ 'mt-2': showControls }"
                >
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
                            class="dropdown-element cartoon-shadow-sm origin-top
                                overflow-hidden rounded-2xl border-2
                                border-border bg-background/20
                                backdrop-blur-3xl"
                            @mousedown.prevent
                            @click="handleSearchAreaInteraction"
                        >
                            <!-- Loading State -->
                            <div
                                v-if="isSearching && searchResults.length === 0"
                                class="p-4"
                            >
                                <div class="flex items-center gap-2">
                                    <div class="flex gap-1">
                                        <span
                                            v-for="i in 3"
                                            :key="i"
                                            class="h-2 w-2 animate-bounce
                                                rounded-full bg-primary/60"
                                            :style="{
                                                animationDelay: `${(i - 1) * 150}ms`,
                                            }"
                                        />
                                    </div>
                                    <span class="text-sm text-muted-foreground"
                                        >Searching...</span
                                    >
                                </div>
                            </div>

                            <!-- Search Results -->
                            <div
                                v-else-if="searchResults.length > 0"
                                ref="searchResultsContainer"
                                class="max-h-64 overflow-y-auto bg-background/20
                                    backdrop-blur-3xl"
                            >
                                <button
                                    v-for="(result, index) in searchResults"
                                    :key="result.word"
                                    :ref="
                                        (el) => {
                                            if (el)
                                                resultRefs[index] =
                                                    el as HTMLButtonElement;
                                        }
                                    "
                                    :class="[
                                        'transition-smooth flex w-full items-center justify-between px-4 py-3 text-left duration-150',
                                        'border-muted-foreground/50 active:scale-[0.98]',
                                        index === selectedIndex
                                            ? 'scale-[1.02] border-l-8 bg-accent/60 pl-4'
                                            : 'border-l-0 pl-4',
                                    ]"
                                    @click="selectResult(result)"
                                    @mouseenter="selectedIndex = index"
                                >
                                    <span
                                        :class="[
                                            'transition-smooth',
                                            index === selectedIndex &&
                                                'font-semibold text-primary',
                                        ]"
                                    >
                                        {{ result.word }}
                                    </span>
                                    <div
                                        class="flex items-center gap-2 text-xs"
                                    >
                                        <span
                                            :class="[
                                                'text-muted-foreground',
                                                index === selectedIndex &&
                                                    'font-semibold text-primary',
                                            ]"
                                        >
                                            {{ result.method }}
                                        </span>
                                        <span
                                            :class="[
                                                'text-muted-foreground',
                                                index === selectedIndex &&
                                                    'font-semibold text-primary',
                                            ]"
                                        >
                                            {{
                                                Math.round(result.score * 100)
                                            }}%
                                        </span>
                                    </div>
                                </button>
                            </div>

                            <!-- No Results Messages -->
                            <div
                                v-else-if="!isSearching && query.length < 2"
                                class="bg-background/50 p-4 text-center text-sm
                                    text-muted-foreground backdrop-blur-sm"
                            >
                                Type at least 2 characters to search...
                            </div>
                            <div
                                v-else-if="!isSearching && query.length >= 2"
                                class="bg-background/50 p-4 text-center text-sm
                                    text-muted-foreground backdrop-blur-sm"
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
import { RefreshCw, Languages, Globe, Trash2 } from 'lucide-vue-next';
import {
    AppleIcon,
    WiktionaryIcon,
    OxfordIcon,
    DictionaryIcon,
} from '@/components/custom/icons';
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
const isDevelopment = ref(import.meta.env.DEV);
const isSearching = ref(false);
const selectedIndex = ref(0);
const aiSuggestions = ref<string[]>([]);
const isContainerHovered = ref(false);
const isFocused = ref(false);
const isShrunken = ref(false);
const regenerateRotation = ref(0);
const isInteractingWithSearchArea = ref(false);

// KISS dropdown state management
const inputFocused = ref(false);
const showControls = ref(false);
const showResults = ref(false);

// Simplified scroll tracking for continuous animations
type SearchBarState = 'normal' | 'hovering' | 'focused';

const currentState = ref<SearchBarState>('normal');
const scrollProgress = ref(0); // 0-1 percentage of page height
const scrollInflectionPoint = ref(0.25); // 25% of page height (configurable)
const documentHeight = ref(0);

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

// KISS: Show search results dropdown when input focused AND query exists AND not doing definition lookup
const shouldShowResults = computed(() => {
    return (
        inputFocused.value &&
        query.value.trim().length > 0 &&
        !store.isSearching
    );
});

// Independent positioning: results always at consistent location
const resultsContainerStyle = computed(() => {
    return {
        paddingTop: '0px',
        transition: 'all 300ms cubic-bezier(0.25, 0.1, 0.25, 1)',
    };
});

// Sync reactive state with computed
watch(shouldShowResults, (newVal) => {
    showResults.value = newVal;
});

watch(
    () => store.showControls,
    (newVal) => {
        showControls.value = newVal;
    },
    { immediate: true }
);

// Simple state transitions for hover/focus only
const transitionToState = (newState: SearchBarState) => {
    if (currentState.value === newState) return;
    currentState.value = newState;
};

// Simplified continuous scroll update without state machine jumps
const updateScrollState = () => {
    if (scrollAnimationFrame) return;

    scrollAnimationFrame = requestAnimationFrame(() => {
        const maxScroll = Math.max(
            documentHeight.value - window.innerHeight,
            1
        );

        // Don't engage scrolling behavior if there's nothing to scroll
        if (maxScroll <= 10) {
            scrollProgress.value = 0;
            scrollAnimationFrame = undefined;
            return;
        }

        // Simple continuous progress calculation
        scrollProgress.value = Math.min(scrollY.value / maxScroll, 1);

        // Update state for icon opacity and container styling
        // Only change states for hover/focus, not based on scroll position
        if (isFocused.value && currentState.value !== 'focused') {
            transitionToState('focused');
        } else if (
            isContainerHovered.value &&
            currentState.value !== 'hovering' &&
            !isFocused.value
        ) {
            transitionToState('hovering');
        } else if (
            !isFocused.value &&
            !isContainerHovered.value &&
            (currentState.value === 'focused' ||
                currentState.value === 'hovering')
        ) {
            transitionToState('normal');
        }

        scrollAnimationFrame = undefined;
    });
};

// Computed opacity for smooth icon fade-out - continuous based on scroll progress
const iconOpacity = computed(() => {
    // Always full opacity when focused or hovered
    if (isFocused.value || isContainerHovered.value) {
        return 1;
    }

    // Don't fade when either dropdown is showing
    if (showControls.value || showResults.value) {
        return 1;
    }

    // Continuous fade based on scroll progress relative to inflection point
    const progress = Math.min(
        scrollProgress.value / scrollInflectionPoint.value,
        1
    );

    // Start fading at 40% of the way to inflection point, fully hidden at 85%
    const fadeStart = 0.4;
    const fadeEnd = 0.85;

    if (progress <= fadeStart) {
        return 1; // Full opacity
    } else if (progress >= fadeEnd) {
        return 0.1; // Nearly hidden but still interactive
    } else {
        // Smooth cubic easing for natural fade
        const fadeProgress = (progress - fadeStart) / (fadeEnd - fadeStart);
        const easedProgress = 1 - Math.pow(1 - fadeProgress, 3); // Cubic ease-out
        return 1 - easedProgress * 0.9; // Fade from 1 to 0.1
    }
});

// Smooth style transitions with optimized max-width for mobile and desktop
const containerStyle = computed(() => {
    const progress = Math.min(
        scrollProgress.value / scrollInflectionPoint.value,
        1
    );

    // Use smaller responsive widths for better desktop experience
    const responsiveMaxWidth = 'min(32rem, calc(100vw - 2rem))';

    // Focused/hovered states or dropdowns shown: full size but responsive
    if (
        isFocused.value ||
        isContainerHovered.value ||
        showControls.value ||
        showResults.value
    ) {
        return {
            maxWidth: responsiveMaxWidth,
            transform: 'scale(1)',
            opacity: '1',
            transition: 'all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        };
    }

    // Smooth continuous shrinking based on scroll progress
    const clampedProgress = Math.max(0, Math.min(progress, 1));

    // Continuous scale transition from 1.0 to 0.88
    const scale = 1 - clampedProgress * 0.12;

    // Continuous opacity transition from 1.0 to 0.92
    const opacity = 1 - clampedProgress * 0.08;

    // Continuous width interpolation between responsiveMaxWidth and minWidth
    // Parse the rem values to interpolate numerically
    const maxWidthStart = 32; // 32rem
    const maxWidthEnd = 24; // 24rem
    const interpolatedWidth =
        maxWidthStart - clampedProgress * (maxWidthStart - maxWidthEnd);
    const currentMaxWidth = `min(${interpolatedWidth}rem, calc(100vw - ${2 + clampedProgress * 2}rem))`;

    return {
        maxWidth: currentMaxWidth,
        transform: `scale(${scale})`,
        opacity: opacity.toString(),
        transition: 'all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    };
});

// Sources configuration
// Type safe sources configuration
interface SourceConfig {
    id: string;
    name: string;
    icon: typeof WiktionaryIcon | typeof OxfordIcon | typeof DictionaryIcon | typeof AppleIcon;
}

const sources: SourceConfig[] = [
    { id: 'wiktionary', name: 'Wiktionary', icon: WiktionaryIcon },
    { id: 'oxford', name: 'Oxford', icon: OxfordIcon },
    { id: 'dictionary_com', name: 'Dictionary.com', icon: DictionaryIcon },
    { id: 'apple_dictionary', name: 'Apple Dictionary', icon: AppleIcon },
];

// Languages configuration with Lucide icons
interface LanguageConfig {
    value: string;
    label: string;
    icon: typeof Globe | typeof Languages;
}

const languages: LanguageConfig[] = [
    { value: 'en', label: 'EN', icon: Globe },
    { value: 'fr', label: 'FR', icon: Languages },
    { value: 'es', label: 'ES', icon: Languages },
    { value: 'de', label: 'DE', icon: Languages },
    { value: 'it', label: 'IT', icon: Languages },
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
    if (!isFocused.value) {
        transitionToState('hovering');
    }
};

const handleMouseLeave = () => {
    isContainerHovered.value = false;
    if (!isFocused.value) {
        transitionToState('normal');
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
    inputFocused.value = true; // KISS: Set input focused state

    // Transition to focused state
    transitionToState('focused');

    if (
        store.sessionState?.searchResults?.length > 0 &&
        query.value.length >= 2
    ) {
        searchResults.value = store.sessionState.searchResults.slice(0, 8);
    }

    nextTick(() => {
        if (searchInput.value && store.searchCursorPosition) {
            const pos = Math.min(
                store.searchCursorPosition,
                query.value.length
            );
            searchInput.value.setSelectionRange(pos, pos);
        }
    });
};

const handleBlur = () => {
    setTimeout(() => {
        if (isInteractingWithSearchArea.value) return;

        isFocused.value = false;
        inputFocused.value = false; // KISS: Clear input focused state

        // KISS: Always hide results on blur (independent of controls)
        showResults.value = false;
        searchResults.value = [];
        isSearching.value = false;

        // Transition back to normal or hovering state
        transitionToState(isContainerHovered.value ? 'hovering' : 'normal');
    }, 150);
};

const handleInput = (event: Event) => {
    const input = event.target as HTMLInputElement;
    store.searchCursorPosition = input.selectionStart || 0;
    performSearch();
};

// Independent close handlers
const closeControls = () => {
    store.showControls = false;
};

const closeResults = () => {
    showResults.value = false;
    searchResults.value = [];
    isSearching.value = false;
};

const handleClose = () => {
    // Close both dropdowns independently
    closeControls();
    closeResults();
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
        Math.min(
            searchResults.value.length - 1,
            selectedIndex.value + direction
        )
    );

    store.searchSelectedIndex = selectedIndex.value;

    // Scroll selected item into view
    nextTick(() => {
        const selectedElement = resultRefs[selectedIndex.value];
        if (selectedElement && searchResultsContainer.value) {
            selectedElement.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest',
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
    // Don't restore focus - let user continue interacting with controls
};

const handleLanguageToggle = (languageCode: string) => {
    store.toggleLanguage(languageCode);
    // Don't restore focus - let user continue interacting with controls
};

const handleModeToggle = () => {
    store.toggleMode();
    // Do not modify focus state when toggling mode
};

const clearAllStorage = () => {
    if (confirm('This will clear all local storage including history and settings. Are you sure?')) {
        // Clear localStorage
        localStorage.clear();
        // Clear sessionStorage
        sessionStorage.clear();
        // Reload the page to reset the app
        window.location.reload();
    }
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

    if (
        wordLower.startsWith(queryLower) &&
        topMatch.word.length > query.value.length
    ) {
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
                searchInput.value.setSelectionRange(
                    query.value.length,
                    query.value.length
                );
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
        if (
            event.key === 'ArrowRight' &&
            currentPosition === query.value.length
        ) {
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
    const searchContainer = target.closest('.search-container');

    if (!searchContainer) {
        // Click completely outside - close both
        handleClose();
        return;
    }

    // Check specific dropdown areas for targeted closing
    const controlsArea = target.closest('[ref="controlsDropdown"]');
    const resultsArea = target.closest('[ref="searchResultsDropdown"]');

    if (!controlsArea && showControls.value) {
        // Clicked outside controls but inside search container
        closeControls();
    }

    if (!resultsArea && showResults.value) {
        // Clicked outside results but inside search container
        closeResults();
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

// Legacy shrink state handling (simplified)
watch(
    [() => props.shrinkPercentage, isContainerHovered],
    ([shrinkPct, hovered]) => {
        if (shrinkPct > 0 && !hovered) {
            isShrunken.value = true;
        } else if (shrinkPct === 0) {
            isShrunken.value = false;
        }
    }
);

// Mounted
onMounted(async () => {
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
