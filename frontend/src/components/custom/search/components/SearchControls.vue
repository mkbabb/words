<template>
    <Transition
        enter-active-class="transition-all duration-350 ease-apple-elastic"
        leave-active-class="transition-all duration-200 ease-apple-bounce-in"
        enter-from-class="opacity-0 scale-90 -translate-y-6 -rotate-1"
        enter-to-class="opacity-100 scale-100 translate-y-0 rotate-0"
        leave-from-class="opacity-100 scale-100 translate-y-0 rotate-0"
        leave-to-class="opacity-0 scale-90 -translate-y-6 -rotate-1"
    >
        <div
            v-if="show"
            ref="controlsDropdown"
            class="dropdown-element cartoon-shadow-sm mb-2 origin-top overflow-hidden rounded-2xl border-2 border-border bg-background/20 backdrop-blur-3xl"
            tabindex="0"
            @mousedown.prevent
            @click="$emit('interaction')"
            @keydown.enter="handleEnterKey"
        >
            <!-- Header: Sidebar Toggle + Search Mode Toggle -->
            <div class="border-border/50 px-4 py-3 flex justify-between items-center lg:justify-center">
                <!-- Mobile Sidebar Toggle (far left) -->
                <button
                    class="lg:hidden p-2 rounded-lg hover:bg-muted/50 transition-colors duration-200"
                    @click="$emit('toggle-sidebar')"
                    title="Toggle Sidebar"
                >
                    <PanelLeft :size="20" class="text-muted-foreground" />
                </button>
                
                <!-- Search Mode Toggle (center on mobile, full width on desktop) -->
                <BouncyToggle
                    :model-value="searchMode"
                    @update:model-value="handleModeChange"
                    :options="[
                        { label: 'Lookup', value: 'lookup' },
                        { label: 'Wordlist', value: 'wordlist' },
                        { label: 'Stage', value: 'stage' },
                    ]"
                    class="text-base font-bold"
                />
                
                <!-- Spacer for mobile layout balance -->
                <div class="lg:hidden w-10"></div>
            </div>

            <!-- Sources (Lookup Mode) -->
            <div
                v-if="searchMode === 'lookup'"
                class="border-t border-border/50 px-4 py-3"
            >
                <h3 class="mb-3 text-sm font-medium">Sources</h3>
                <div class="flex flex-wrap gap-2">
                    <button
                        v-for="source in DICTIONARY_SOURCES"
                        :key="source.id"
                        @click="toggleSource(source.id)"
                        @keydown.enter.stop.prevent="toggleSource(source.id)"
                        :disabled="noAI && selectedSources.length > 0 && !selectedSources.includes(source.id)"
                        :class="[
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-apple-spring',
                            selectedSources.includes(source.id)
                                ? 'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 hover:scale-[1.05] active:scale-[0.97]'
                                : noAI && selectedSources.length > 0
                                    ? 'bg-muted/50 text-muted-foreground/50 cursor-not-allowed'
                                    : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <component :is="source.icon" :size="16" />
                        {{ source.name }}
                    </button>
                </div>
            </div>

            <!-- Languages (Lookup Mode) -->
            <div
                v-if="searchMode === 'lookup'"
                class="border-t border-border/50 px-4 py-3"
            >
                <h3 class="mb-3 text-sm font-medium">Languages</h3>
                <div class="flex flex-wrap gap-2">
                    <button
                        v-for="language in LANGUAGES"
                        :key="language.value"
                        @click="toggleLanguage(language.value)"
                        @keydown.enter.stop.prevent="toggleLanguage(language.value)"
                        :class="[
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-apple-spring',
                            selectedLanguages.includes(language.value)
                                ? 'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 hover:scale-[1.05] active:scale-[0.97]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <component :is="language.icon" :size="16" />
                        {{ language.label }}
                    </button>
                </div>
            </div>

            <!-- Wordlist Filters -->
            <div
                v-if="searchMode === 'wordlist'"
                class="border-t border-border/50 px-4 py-3"
            >
                <h3 class="mb-3 text-sm font-medium">Mastery Levels</h3>
                <div class="flex flex-wrap gap-2">
                    <button
                        @click="toggleFilter('showBronze')"
                        :class="[
                            'cursor-pointer select-none flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-out',
                            wordlistFilters.showBronze
                                ? 'bg-gradient-to-r from-orange-400 to-orange-600 text-white shadow-sm hover:shadow-md hover:scale-[1.05] active:scale-[0.97]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <div class="w-2 h-2 rounded-full bg-gradient-to-r from-orange-400 to-orange-600"></div>
                        Learning
                    </button>
                    <button
                        @click="toggleFilter('showSilver')"
                        :class="[
                            'cursor-pointer select-none flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-out',
                            wordlistFilters.showSilver
                                ? 'bg-gradient-to-r from-gray-400 to-gray-600 text-white shadow-sm hover:shadow-md hover:scale-[1.05] active:scale-[0.97]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <div class="w-2 h-2 rounded-full bg-gradient-to-r from-gray-400 to-gray-600"></div>
                        Familiar
                    </button>
                    <button
                        @click="toggleFilter('showGold')"
                        :class="[
                            'cursor-pointer select-none flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-out',
                            wordlistFilters.showGold
                                ? 'bg-gradient-to-r from-yellow-400 to-amber-600 text-white shadow-sm hover:shadow-md hover:scale-[1.05] active:scale-[0.97]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <div class="w-2 h-2 rounded-full bg-gradient-to-r from-yellow-400 to-amber-600"></div>
                        Mastered
                    </button>
                </div>
            </div>

            <!-- Wordlist Additional Filters -->
            <div
                v-if="searchMode === 'wordlist'"
                class="border-t border-border/50 px-4 py-3"
            >
                <h3 class="mb-3 text-sm font-medium">Additional Filters</h3>
                <div class="flex flex-wrap gap-2">
                    <button
                        @click="toggleFilter('showHotOnly')"
                        :class="[
                            'cursor-pointer select-none flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-out',
                            wordlistFilters.showHotOnly
                                ? 'bg-red-500 text-white shadow-sm hover:bg-red-600 hover:shadow-md hover:scale-[1.05] active:scale-[0.97]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <Flame :size="14" />
                        Hot Only
                    </button>
                    <button
                        @click="toggleFilter('showDueOnly')"
                        :class="[
                            'cursor-pointer select-none flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-out',
                            wordlistFilters.showDueOnly
                                ? 'bg-blue-500 text-white shadow-sm hover:bg-blue-600 hover:shadow-md hover:scale-[1.05] active:scale-[0.97]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <Clock :size="14" />
                        Due for Review
                    </button>
                </div>
            </div>

            <!-- Wordlist Sort Order -->
            <div
                v-if="searchMode === 'wordlist'"
                class="border-t border-border/50 px-4 py-3"
            >
                <h3 class="mb-3 text-sm font-medium">Sort Order</h3>
                <WordListSortBuilder v-model="wordlistSortCriteria" />
            </div>


            <!-- Actions Row -->
            <div
                v-if="searchMode === 'lookup'"
                class="border-t border-border/50 px-4 py-3"
            >
                <h3 class="mb-3 text-sm font-medium">Actions</h3>
                <ActionsRow
                    v-model:no-a-i="noAI"
                    :show-refresh-button="showRefreshButton"
                    :force-refresh-mode="forceRefreshMode"
                    :is-development="isDevelopment"
                    @clear-storage="emit('clear-storage')"
                    @toggle-sidebar="emit('toggle-sidebar')"
                    @toggle-refresh="emit('toggle-refresh')"
                />
            </div>

            <!-- AI Suggestions -->
            <div
                v-if="searchMode === 'lookup' && aiSuggestions.length > 0"
                class="border-t border-border/50 px-4 py-3"
            >
                <div class="flex flex-wrap items-center justify-center gap-2">
                    <Button
                        v-for="word in aiSuggestions"
                        :key="word"
                        variant="outline"
                        size="default"
                        class="hover-text-grow flex-shrink-0 text-sm whitespace-nowrap font-medium bg-yellow-500/10 border-yellow-500/20 hover:bg-yellow-500/20 hover:border-yellow-500/30"
                        @click="$emit('word-select', word)"
                        @keydown.enter.stop="$emit('word-select', word)"
                    >
                        {{ word }}
                    </Button>
                </div>
            </div>
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { useStores } from '@/stores';
import { Button } from '@/components/ui';
import { BouncyToggle } from '@/components/custom/animation';
import { Flame, Clock, PanelLeft } from 'lucide-vue-next';
import ActionsRow from './ActionsRow.vue';
import WordListSortBuilder from '../../wordlist/WordListSortBuilder.vue';
import { DICTIONARY_SOURCES, LANGUAGES } from '../constants/sources';
import type { SearchMode } from '../types';

interface SearchControlsProps {
    show: boolean;
    aiSuggestions: string[];
    isDevelopment: boolean;
    showRefreshButton?: boolean;
    forceRefreshMode?: boolean;
}

const props = defineProps<SearchControlsProps>();

// Modern Vue 3.4+ patterns - using defineModel for two-way bindings
const router = useRouter();
const { searchConfig, searchBar } = useStores();
// ✅ Make component reactive to store changes instead of using defineModel
const searchMode = computed(() => searchConfig.searchMode);
const selectedSources = defineModel<string[]>('selectedSources', { required: true });
const selectedLanguages = defineModel<string[]>('selectedLanguages', { required: true });
const noAI = defineModel<boolean>('noAI', { required: true });
const wordlistFilters = defineModel<{
    showBronze: boolean;
    showSilver: boolean;
    showGold: boolean;
    showHotOnly: boolean;
    showDueOnly: boolean;
}>('wordlistFilters', { 
    required: false,
    default: () => ({
        showBronze: true,
        showSilver: true,
        showGold: true,
        showHotOnly: false,
        showDueOnly: false,
    })
});


const wordlistSortCriteria = defineModel<any[]>('wordlistSortCriteria', { 
    required: false,
    default: () => []
});

const emit = defineEmits<{
    'word-select': [word: string];
    'clear-storage': [];
    'interaction': [];
    'toggle-sidebar': [];
    'toggle-refresh': [];
    'execute-search': [];
}>();


// Helper functions for toggling
const toggleSource = (sourceId: string) => {
    // In no-AI mode, only allow one source at a time
    if (noAI.value) {
        if (selectedSources.value.includes(sourceId)) {
            // Deselect if already selected
            selectedSources.value = [];
        } else {
            // Select only this source
            selectedSources.value = [sourceId];
        }
    } else {
        // Normal multi-select behavior
        const index = selectedSources.value.indexOf(sourceId);
        if (index > -1) {
            selectedSources.value.splice(index, 1);
        } else {
            selectedSources.value.push(sourceId);
        }
    }
};

const toggleLanguage = (languageCode: string) => {
    const index = selectedLanguages.value.indexOf(languageCode);
    if (index > -1) {
        selectedLanguages.value.splice(index, 1);
    } else {
        selectedLanguages.value.push(languageCode);
    }
};

const toggleFilter = (filterKey: keyof typeof wordlistFilters.value) => {
    // Create a new object with the toggled value to trigger reactivity
    wordlistFilters.value = {
        ...wordlistFilters.value,
        [filterKey]: !wordlistFilters.value[filterKey]
    };
};

const controlsDropdown = ref<HTMLDivElement>();

// Emit is used in template
void emit;

// Handle enter key press
const handleEnterKey = (event: KeyboardEvent) => {
    event.preventDefault();
    event.stopPropagation();
    emit('execute-search');
};

// Handle mode change from BouncyToggle
const handleModeChange = async (newMode: string | SearchMode) => {
    console.log('🎛️ SearchControls handleModeChange:', searchMode.value, '->', newMode);
    const typedMode = newMode as SearchMode;
    if (typedMode !== searchMode.value) {
        console.log('✅ Using simple mode setter with query management');
        // ✅ Save current query and switch mode - returns saved query for new mode
        const currentQuery = searchBar.searchQuery;
        const savedQuery = await searchConfig.setMode(typedMode, currentQuery);
        
        // Update search bar with the saved query for the new mode
        if (savedQuery) {
            searchBar.setQuery(savedQuery);
        } else if (typedMode !== 'lookup') {
            // Clear query for non-lookup modes if no saved query
            searchBar.setQuery('');
        }
        
        // ✅ Basic navigation - just go to Home to reflect mode change
        router.push({ name: 'Home' });
        console.log('🧭 Navigated to Home for mode:', typedMode);
    }
};

// When noAI mode changes, ensure only one source is selected
watch(noAI, (newValue) => {
    if (newValue && selectedSources.value.length > 1) {
        // Keep only the first source when entering no-AI mode
        selectedSources.value = [selectedSources.value[0]];
    }
});

// Global enter key handler when controls are visible
const handleGlobalEnter = (event: KeyboardEvent) => {
    if (!props.show) return;
    
    // When controls are visible, any enter key press should execute search
    event.preventDefault();
    event.stopPropagation();
    emit('execute-search');
};

// Store the event handler reference for cleanup
const keydownHandler = (e: KeyboardEvent) => {
    if (e.key === 'Enter') {
        handleGlobalEnter(e);
    }
};

// Setup enter key handling when component mounts or when show prop changes
const setupEnterKeyHandling = async () => {
    await nextTick();
    
    // No need to focus, as it might interfere with button clicks
};

// Watch for when controls are shown
watch(() => props.show, async (newVal) => {
    if (newVal) {
        await setupEnterKeyHandling();
    }
});

onMounted(() => {
    // Use capture phase to catch events before they bubble
    document.addEventListener('keydown', keydownHandler, true);
    
    // Setup initial handling if already shown
    if (props.show) {
        setupEnterKeyHandling();
    }
});

onUnmounted(() => {
    document.removeEventListener('keydown', keydownHandler, true);
});

// Note: SearchMode switching is handled directly via v-model binding to store.searchMode
// The BouncyToggle component automatically updates the store when user clicks
// No watcher needed here as the store's reactivity handles the rest

defineExpose({
    element: controlsDropdown
});
</script>