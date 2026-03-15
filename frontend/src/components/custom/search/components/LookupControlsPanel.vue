<template>
    <!-- Sources -->
    <div class="border-t border-border/50 px-4 py-3">
        <h3 class="mb-3 text-sm font-medium">Sources</h3>
        <div class="flex flex-wrap gap-2">
            <HoverCard
                v-for="source in DICTIONARY_SOURCES"
                :key="source.id"
                :open-delay="400"
                :close-delay="100"
            >
                <HoverCardTrigger as-child>
                    <button
                        @click="toggleSource(source.id)"
                        @keydown.enter.stop.prevent="toggleSource(source.id)"
                        :disabled="
                            noAI &&
                            selectedSources.length > 0 &&
                            !selectedSources.includes(source.id)
                        "
                        :class="[
                            'flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ease-apple-spring select-none active:scale-[0.97]',
                            selectedSources.includes(source.id)
                                ? 'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 hover:scale-[1.05]'
                                : noAI && selectedSources.length > 0
                                  ? 'cursor-not-allowed bg-muted/50 text-muted-foreground/50'
                                  : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03]',
                        ]"
                    >
                        <component :is="source.icon" :size="16" />
                        {{ source.name }}
                    </button>
                </HoverCardTrigger>
                <HoverCardContent class="w-auto p-2" side="top">
                    <p class="text-sm">{{ selectedSources.includes(source.id) ? 'Remove' : 'Add' }} {{ source.name }}</p>
                </HoverCardContent>
            </HoverCard>
        </div>
    </div>

    <!-- Languages -->
    <div class="border-t border-border/50 px-4 py-3">
        <h3 class="mb-3 text-sm font-medium">Languages</h3>
        <div class="flex flex-wrap gap-2">
            <HoverCard
                v-for="language in LANGUAGES"
                :key="language.value"
                :open-delay="400"
                :close-delay="100"
            >
                <HoverCardTrigger as-child>
                    <button
                        @click="toggleLanguage(language.value)"
                        @keydown.enter.stop.prevent="toggleLanguage(language.value)"
                        :class="[
                            'flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ease-apple-spring select-none active:scale-[0.97]',
                            selectedLanguages.includes(language.value)
                                ? 'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 hover:scale-[1.05]'
                                : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03]',
                        ]"
                    >
                        <component :is="language.icon" :size="16" />
                        {{ language.label }}
                    </button>
                </HoverCardTrigger>
                <HoverCardContent class="w-auto p-2" side="top">
                    <p class="text-sm">{{ selectedLanguages.includes(language.value) ? 'Remove' : 'Add' }} {{ language.label }}</p>
                </HoverCardContent>
            </HoverCard>
        </div>
    </div>

    <!-- Search Method -->
    <div class="border-t border-border/50 px-4 py-3">
        <h3 class="mb-3 text-sm font-medium">Search Method</h3>
        <BouncyToggle
            :model-value="currentSearchMode"
            @update:model-value="handleSearchModeChange"
            :options="searchModeOptions"
            class="text-sm font-medium"
        />
        <p class="mt-2 text-xs text-muted-foreground">
            {{ searchModeDescriptions[String(currentSearchMode)] }}
        </p>
    </div>

    <!-- Actions Row -->
    <div class="border-t border-border/50 px-4 py-3">
        <h3 class="mb-3 text-sm font-medium">Actions</h3>
        <ActionsRow
            v-model:no-a-i="noAI"
            :show-refresh-button="showRefreshButton"
            :force-refresh-mode="forceRefreshMode"
            :is-development="isDevelopment"
            @clear-storage="$emit('clear-storage')"
            @toggle-sidebar="$emit('toggle-sidebar')"
            @toggle-refresh="$emit('toggle-refresh')"
        />
    </div>

    <!-- AI Suggestions -->
    <div
        v-if="aiSuggestions.length > 0"
        class="border-t border-border/50 px-4 py-3"
    >
        <div class="flex flex-wrap items-center justify-center gap-2">
            <Button
                v-for="word in aiSuggestions"
                :key="word"
                variant="outline"
                size="default"
                class="hover-text-grow flex-shrink-0 border-yellow-500/20 bg-yellow-500/10 text-sm font-medium whitespace-nowrap hover:border-yellow-500/30 hover:bg-yellow-500/20"
                @click="$emit('word-select', word)"
                @keydown.enter.stop="$emit('word-select', word)"
            >
                {{ word }}
            </Button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { useStores } from '@/stores';
import { Button } from '@/components/ui';
import { BouncyToggle } from '@/components/custom/animation';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import ActionsRow from './ActionsRow.vue';
import { DICTIONARY_SOURCES, LANGUAGES } from '../constants/sources';

interface LookupControlsPanelProps {
    aiSuggestions: string[];
    isDevelopment: boolean;
    showRefreshButton?: boolean;
    forceRefreshMode?: boolean;
}

defineProps<LookupControlsPanelProps>();

const selectedSources = defineModel<string[]>('selectedSources', {
    required: true,
});
const selectedLanguages = defineModel<string[]>('selectedLanguages', {
    required: true,
});
const noAI = defineModel<boolean>('noAI', { required: true });

defineEmits<{
    'word-select': [word: string];
    'clear-storage': [];
    'toggle-sidebar': [];
    'toggle-refresh': [];
}>();

const { lookupMode } = useStores();
const { semanticStatus } = storeToRefs(lookupMode);
const currentSearchMode = computed(() => {
    const mode = lookupMode.searchMode;
    return Array.isArray(mode) ? mode[0] || 'smart' : mode;
});

// Semantic status computeds
const semanticAvailable = computed(() => semanticStatus.value?.ready === true);
const semanticUnavailable = computed(() => !semanticAvailable.value && semanticStatus.value !== null);

const semanticTooltip = computed(() => {
    const s = semanticStatus.value;
    if (!s) return undefined;
    if (s.ready) return undefined;
    if (!s.enabled) return 'Semantic search is disabled';
    if (s.building) return 'Semantic search building in background';
    return s.message || 'Semantic search unavailable';
});

const searchModeOptions = computed(() => [
    { label: 'Smart', value: 'smart', icon: 'Zap', tooltip: semanticTooltip.value },
    { label: 'Exact', value: 'exact', icon: 'Target' },
    { label: 'Fuzzy', value: 'fuzzy', icon: 'Sparkles' },
    { label: 'Semantic', value: 'semantic', icon: 'Search', disabled: semanticUnavailable.value, tooltip: semanticTooltip.value },
]);

// Search mode descriptions
const searchModeDescriptions: Record<string, string> = {
    smart: 'Adaptive search that combines exact, fuzzy, and semantic matching',
    exact: 'Find exact word matches only',
    fuzzy: 'Find similar words and handle typos',
    semantic: 'Find words with similar meanings using AI',
};

// Helper functions for toggling
const toggleSource = (sourceId: string) => {
    if (noAI.value) {
        if (selectedSources.value.includes(sourceId)) {
            selectedSources.value = [];
        } else {
            selectedSources.value = [sourceId];
        }
    } else {
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
        selectedLanguages.value = selectedLanguages.value.filter(
            (value) => value !== languageCode
        );
    } else {
        selectedLanguages.value = [
            languageCode,
            ...selectedLanguages.value.filter((value) => value !== languageCode),
        ];
    }
};

const handleSearchModeChange = (mode: string | string[]) => {
    if (Array.isArray(mode)) return;
    lookupMode.setSearchMode(mode as 'smart' | 'exact' | 'fuzzy' | 'semantic');
};

// When noAI mode changes, ensure only one source is selected
watch(noAI, (newValue) => {
    if (newValue && selectedSources.value.length > 1) {
        selectedSources.value = [selectedSources.value[0]];
    }
});
</script>
