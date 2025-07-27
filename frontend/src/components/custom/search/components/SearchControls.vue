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
                        :class="[
                            'hover-lift flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200',
                            selectedSources.includes(source.id)
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

            <!-- Settings Row (DEBUG) -->
            <div
                v-if="isDevelopment && searchMode === 'lookup'"
                class="border-t border-border/50 px-4 py-3"
            >
                <h3 class="mb-3 text-sm font-medium">Settings</h3>
                <div class="grid grid-cols-4 gap-2">
                    <button
                        @click="$emit('clear-storage')"
                        class="hover-lift flex items-center justify-center rounded-lg bg-red-50 dark:bg-red-500/10 p-2 text-red-600 dark:text-red-500 transition-all duration-200 hover:bg-red-100 dark:hover:bg-red-500/20"
                        title="Clear All Storage"
                    >
                        <Trash2 
                            :size="16" 
                            class="text-muted-foreground/70 transition-colors duration-200 hover:text-destructive dark:text-muted-foreground"
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
import { ref } from 'vue';
import { Trash2 } from 'lucide-vue-next';
import { Button } from '@/components/ui';
import { BouncyToggle } from '@/components/custom/animation';
import { DICTIONARY_SOURCES, LANGUAGES } from '../constants/sources';
import type { SearchMode } from '../types';

interface SearchControlsProps {
    show: boolean;
    aiSuggestions: string[];
    isDevelopment: boolean;
}

defineProps<SearchControlsProps>();

// Modern Vue 3.4+ patterns - using defineModel for two-way bindings
const searchMode = defineModel<SearchMode>('searchMode', { required: true });
const selectedSources = defineModel<string[]>('selectedSources', { required: true });
const selectedLanguages = defineModel<string[]>('selectedLanguages', { required: true });

const emit = defineEmits<{
    'word-select': [word: string];
    'clear-storage': [];
    'interaction': [];
}>();

// Helper functions for toggling
const toggleSource = (sourceId: string) => {
    const index = selectedSources.value.indexOf(sourceId);
    if (index > -1) {
        selectedSources.value.splice(index, 1);
    } else {
        selectedSources.value.push(sourceId);
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

defineExpose({
    element: controlsDropdown
});
</script>