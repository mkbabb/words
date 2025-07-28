<template>
    <Transition
        enter-active-class="transition-all duration-300 ease-apple-bounce"
        leave-active-class="transition-all duration-300 ease-apple-bounce"
        enter-from-class="opacity-0 scale-95 -translate-y-4"
        enter-to-class="opacity-100 scale-100 translate-y-0"
        leave-from-class="opacity-100 scale-100 translate-y-0"
        leave-to-class="opacity-0 scale-95 -translate-y-4"
    >
        <div
            v-if="show"
            ref="controlsDropdown"
            class="dropdown-element cartoon-shadow-sm mb-2 origin-top overflow-hidden rounded-2xl border-2 border-border bg-background/20 backdrop-blur-3xl"
            @mousedown.prevent
            @click="$emit('interaction')"
        >
            <!-- Search Mode Toggle -->
            <div class="border-border/50 px-4 py-3">
                <h3 class="mb-3 text-sm font-medium">Mode</h3>
                <BouncyToggle
                    v-model="searchMode"
                    :options="[
                        { label: 'Lookup', value: 'lookup' },
                        { label: 'Wordlist', value: 'wordlist' },
                        { label: 'Stage', value: 'stage' },
                    ]"
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
                        :disabled="noAI && selectedSources.length > 0 && !selectedSources.includes(source.id)"
                        :class="[
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200',
                            selectedSources.includes(source.id)
                                ? 'bg-primary text-primary-foreground shadow-sm'
                                : noAI && selectedSources.length > 0
                                    ? 'bg-muted/50 text-muted-foreground/50 cursor-not-allowed'
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
                v-if="searchMode === 'lookup'"
                class="border-t border-border/50 px-4 py-3"
            >
                <h3 class="mb-3 text-sm font-medium">Languages</h3>
                <div class="flex flex-wrap gap-2">
                    <button
                        v-for="language in LANGUAGES"
                        :key="language.value"
                        @click="toggleLanguage(language.value)"
                        :class="[
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200',
                            selectedLanguages.includes(language.value)
                                ? 'bg-primary text-primary-foreground shadow-sm'
                                : 'bg-muted text-muted-foreground hover:bg-muted/80',
                        ]"
                    >
                        <component :is="language.icon" :size="16" />
                        {{ language.label }}
                    </button>
                </div>
            </div>

            <!-- Actions Row -->
            <div
                v-if="searchMode === 'lookup'"
                class="border-t border-border/50 px-4 py-3"
            >
                <h3 class="mb-3 text-sm font-medium">Actions</h3>
                <div class="flex gap-2 justify-start">
                    <!-- Sidebar Toggle (Mobile Only) -->
                    <button
                        v-if="isMobile"
                        @click="$emit('toggle-sidebar')"
                        class="group hover-lift flex items-center justify-center rounded-lg bg-muted p-2 transition-all duration-200 hover:bg-muted/80"
                        title="Toggle Sidebar"
                    >
                        <PanelLeft 
                            :size="16" 
                            class="text-foreground/70 transition-all duration-200 group-hover:scale-110"
                        />
                    </button>
                    
                    <!-- AI Mode Toggle -->
                    <button
                        @click="handleAIToggle"
                        :class="[
                            'group hover-lift flex items-center justify-center rounded-lg p-2 transition-all duration-200',
                            !noAI
                                ? 'bg-primary/20 text-primary hover:bg-primary/30'
                                : 'bg-muted text-foreground/70 hover:bg-muted/80 hover:text-foreground'
                        ]"
                        :title="!noAI ? 'AI synthesis enabled' : 'Raw provider data only'"
                    >
                        <Wand2 
                            :size="16" 
                            :class="[
                                'transition-all duration-300',
                                aiAnimating && 'animate-sparkle',
                                'group-hover:scale-110'
                            ]"
                        />
                    </button>
                    
                    <!-- Force Refresh Toggle -->
                    <button
                        v-if="showRefreshButton"
                        @click="handleRefreshToggle"
                        :class="[
                            'group hover-lift flex items-center justify-center rounded-lg p-2 transition-all duration-200',
                            forceRefreshMode
                                ? 'bg-primary/20 text-primary hover:bg-primary/30'
                                : 'bg-muted text-foreground/70 hover:bg-muted/80 hover:text-foreground'
                        ]"
                        :title="forceRefreshMode ? 'Force refresh mode ON' : 'Toggle force refresh mode'"
                    >
                        <RefreshCw 
                            :size="16" 
                            :class="[
                                'transition-all duration-300',
                                'group-hover:rotate-180 group-hover:scale-110',
                                forceRefreshMode && 'animate-spin-slow'
                            ]"
                        />
                    </button>
                    
                    <!-- Clear Storage (Debug) -->
                    <button
                        v-if="isDevelopment"
                        @click="handleClearStorage"
                        :class="[
                            'group hover-lift flex items-center justify-center rounded-lg p-2 transition-all duration-200',
                            'bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-500',
                            'hover:bg-red-100 dark:hover:bg-red-500/20 hover:text-red-700 dark:hover:text-red-400'
                        ]"
                        :title="'Clear All Storage'"
                    >
                        <Trash2 
                            :size="16" 
                            :class="[
                                'transition-all duration-300',
                                'group-hover:scale-110',
                                trashAnimating && 'animate-wiggle'
                            ]"
                        />
                    </button>
                </div>
            </div>

            <!-- AI Suggestions -->
            <div
                v-if="searchMode === 'lookup' && aiSuggestions.length > 0"
                class="border-t border-border/50 px-4 py-3"
            >
                <div class="flex flex-col items-center gap-3">
                    <div class="flex flex-wrap items-center justify-center gap-2">
                        <Button
                            v-for="word in aiSuggestions"
                            :key="word"
                            variant="outline"
                            size="default"
                            class="hover-text-grow flex-shrink-0 text-sm whitespace-nowrap font-medium"
                            @click="$emit('word-select', word)"
                        >
                            {{ word }}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { Trash2, PanelLeft, RefreshCw, Wand2 } from 'lucide-vue-next';
import { Button } from '@/components/ui';
import { BouncyToggle } from '@/components/custom/animation';
import { DICTIONARY_SOURCES, LANGUAGES } from '../constants/sources';
import type { SearchMode } from '../types';

interface SearchControlsProps {
    show: boolean;
    aiSuggestions: string[];
    isDevelopment: boolean;
    showRefreshButton?: boolean;
    forceRefreshMode?: boolean;
}

defineProps<SearchControlsProps>();

// Modern Vue 3.4+ patterns - using defineModel for two-way bindings
const searchMode = defineModel<SearchMode>('searchMode', { required: true });
const selectedSources = defineModel<string[]>('selectedSources', { required: true });
const selectedLanguages = defineModel<string[]>('selectedLanguages', { required: true });
const noAI = defineModel<boolean>('noAI', { required: true });

const emit = defineEmits<{
    'word-select': [word: string];
    'clear-storage': [];
    'interaction': [];
    'toggle-sidebar': [];
    'toggle-refresh': [];
}>();

// Reactive window width
const windowWidth = ref(window.innerWidth);

// Check if mobile
const isMobile = computed(() => windowWidth.value < 768);

// Handle window resize
const handleResize = () => {
    windowWidth.value = window.innerWidth;
};

// Set up resize listener
onMounted(() => {
    window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
    window.removeEventListener('resize', handleResize);
});

// Animation states
const aiAnimating = ref(false);
const trashAnimating = ref(false);

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

const controlsDropdown = ref<HTMLDivElement>();

// Emit is used in template
void emit;

// Event handlers
const handleAIToggle = () => {
    noAI.value = !noAI.value;
    aiAnimating.value = true;
    setTimeout(() => {
        aiAnimating.value = false;
    }, 600);
};

const handleRefreshToggle = () => {
    emit('toggle-refresh');
};

const handleClearStorage = () => {
    trashAnimating.value = true;
    setTimeout(() => {
        trashAnimating.value = false;
        emit('clear-storage');
    }, 600);
};

// When noAI mode changes, ensure only one source is selected
watch(noAI, (newValue) => {
    if (newValue && selectedSources.value.length > 1) {
        // Keep only the first source when entering no-AI mode
        selectedSources.value = [selectedSources.value[0]];
    }
});

defineExpose({
    element: controlsDropdown
});
</script>