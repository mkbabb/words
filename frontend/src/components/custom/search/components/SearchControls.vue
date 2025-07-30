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
            <!-- Search Mode Toggle -->
            <div class="border-border/50 px-4 py-3 flex justify-center">
                <BouncyToggle
                    v-model="searchMode"
                    :options="[
                        { label: 'Lookup', value: 'lookup' },
                        { label: 'Wordlist', value: 'wordlist' },
                        { label: 'Stage', value: 'stage' },
                    ]"
                    class="text-base font-bold"
                />
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
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-apple-spring',
                            wordlistFilters.showBronze
                                ? 'bg-gradient-to-r from-orange-400 to-orange-600 text-white shadow-sm hover:scale-[1.05] active:scale-[0.97]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <div class="w-2 h-2 rounded-full bg-gradient-to-r from-orange-400 to-orange-600"></div>
                        Learning
                    </button>
                    <button
                        @click="toggleFilter('showSilver')"
                        :class="[
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-apple-spring',
                            wordlistFilters.showSilver
                                ? 'bg-gradient-to-r from-gray-400 to-gray-600 text-white shadow-sm hover:scale-[1.05] active:scale-[0.97]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <div class="w-2 h-2 rounded-full bg-gradient-to-r from-gray-400 to-gray-600"></div>
                        Familiar
                    </button>
                    <button
                        @click="toggleFilter('showGold')"
                        :class="[
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-apple-spring',
                            wordlistFilters.showGold
                                ? 'bg-gradient-to-r from-yellow-400 to-amber-600 text-white shadow-sm hover:scale-[1.05] active:scale-[0.97]'
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
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-apple-spring',
                            wordlistFilters.showHotOnly
                                ? 'bg-red-500 text-white shadow-sm hover:bg-red-600 hover:scale-[1.05] active:scale-[0.97]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <Flame :size="14" />
                        Hot Only
                    </button>
                    <button
                        @click="toggleFilter('showDueOnly')"
                        :class="[
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-apple-spring',
                            wordlistFilters.showDueOnly
                                ? 'bg-blue-500 text-white shadow-sm hover:bg-blue-600 hover:scale-[1.05] active:scale-[0.97]'
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

            <!-- Wordlist Chunking Options -->
            <div
                v-if="searchMode === 'wordlist'"
                class="border-t border-border/50 px-4 py-3"
            >
                <h3 class="mb-3 text-sm font-medium">Chunk View</h3>
                <div class="flex flex-wrap gap-2">
                    <button
                        @click="toggleChunking('byMastery')"
                        :class="[
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-apple-spring',
                            wordlistChunking.byMastery
                                ? 'bg-purple-500 text-white shadow-sm hover:bg-purple-600 hover:scale-[1.05] active:scale-[0.97]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <Trophy :size="14" />
                        By Mastery
                    </button>
                    <button
                        @click="toggleChunking('byDate')"
                        :class="[
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-apple-spring',
                            wordlistChunking.byDate
                                ? 'bg-green-500 text-white shadow-sm hover:bg-green-600 hover:scale-[1.05] active:scale-[0.97]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <Calendar :size="14" />
                        By Date Added
                    </button>
                    <button
                        @click="toggleChunking('byLastVisited')"
                        :class="[
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-apple-spring',
                            wordlistChunking.byLastVisited
                                ? 'bg-blue-500 text-white shadow-sm hover:bg-blue-600 hover:scale-[1.05] active:scale-[0.97]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <Eye :size="14" />
                        By Last Visited
                    </button>
                    <button
                        @click="toggleChunking('byFrequency')"
                        :class="[
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-300 ease-apple-spring',
                            wordlistChunking.byFrequency
                                ? 'bg-orange-500 text-white shadow-sm hover:bg-orange-600 hover:scale-[1.05] active:scale-[0.97]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03] active:scale-[0.98]',
                        ]"
                    >
                        <BarChart3 :size="14" />
                        By Frequency
                    </button>
                </div>
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
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { Button } from '@/components/ui';
import { BouncyToggle } from '@/components/custom/animation';
import { Flame, Clock, Trophy, Calendar, Eye, BarChart3 } from 'lucide-vue-next';
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
const searchMode = defineModel<SearchMode>('searchMode', { required: true });
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

const wordlistChunking = defineModel<{
    byMastery: boolean;
    byDate: boolean;
    byLastVisited: boolean;
    byFrequency: boolean;
}>('wordlistChunking', { 
    required: false,
    default: () => ({
        byMastery: false,
        byDate: false,
        byLastVisited: false,
        byFrequency: false,
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
    wordlistFilters.value[filterKey] = !wordlistFilters.value[filterKey];
};

const toggleChunking = (chunkKey: keyof typeof wordlistChunking.value) => {
    // Only allow one chunking method at a time
    Object.keys(wordlistChunking.value).forEach(key => {
        wordlistChunking.value[key as keyof typeof wordlistChunking.value] = false;
    });
    wordlistChunking.value[chunkKey] = true;
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

defineExpose({
    element: controlsDropdown
});
</script>