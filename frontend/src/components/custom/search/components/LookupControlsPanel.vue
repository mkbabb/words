<template>
    <!-- Providers -->
    <div class="border-t border-border px-4 py-3">
        <h3 class="mb-3 text-sm font-medium">Providers</h3>
        <div class="flex flex-wrap gap-3">
            <Tooltip
                v-for="source in DICTIONARY_SOURCES"
                :key="source.id"
            >
                <TooltipTrigger as-child>
                    <button
                        @click="toggleSource(source.id)"
                        @keydown.enter.stop.prevent="toggleSource(source.id)"
                        :class="[
                            'flex h-10 w-10 items-center justify-center rounded-full border transition-all duration-200 ease-apple-spring select-none active:scale-[0.95]',
                            selectedSources.includes(source.id)
                                ? 'border-primary/40 bg-primary/10 ring-2 ring-primary/20 shadow-sm'
                                : 'border-border/20 bg-muted/80 hover:bg-muted hover:border-border/40',
                        ]"
                    >
                        <component
                            :is="source.icon"
                            :size="20"
                            :class="selectedSources.includes(source.id) ? 'text-primary' : 'text-muted-foreground'"
                        />
                    </button>
                </TooltipTrigger>
                <TooltipContent side="top" :side-offset="6">
                    {{ source.name }}
                </TooltipContent>
            </Tooltip>
        </div>
    </div>

    <!-- Languages -->
    <div class="border-t border-border px-4 py-3">
        <h3 class="mb-3 text-sm font-medium">Languages</h3>
        <div class="flex flex-wrap gap-3">
            <Tooltip
                v-for="language in LANGUAGES"
                :key="language.value"
            >
                <TooltipTrigger as-child>
                    <button
                        @click="toggleLanguage(language.value)"
                        @keydown.enter.stop.prevent="toggleLanguage(language.value)"
                        :class="[
                            'flex h-10 w-10 items-center justify-center rounded-full border text-xs font-semibold uppercase transition-all duration-200 ease-apple-spring select-none active:scale-[0.95]',
                            selectedLanguages.includes(language.value)
                                ? 'border-primary/40 bg-primary/10 text-primary ring-2 ring-primary/20 shadow-sm'
                                : 'border-border/20 bg-muted/80 text-muted-foreground hover:bg-muted hover:border-border/40 hover:text-foreground',
                        ]"
                    >
                        {{ language.label }}
                    </button>
                </TooltipTrigger>
                <TooltipContent side="top" :side-offset="6">
                    {{ language.label === 'EN' ? 'English' : language.label === 'FR' ? 'French' : language.label === 'ES' ? 'Spanish' : language.label === 'DE' ? 'German' : language.label === 'IT' ? 'Italian' : language.label }}
                </TooltipContent>
            </Tooltip>
        </div>
    </div>

    <!-- Search Method -->
    <div class="border-t border-border px-4 py-3">
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
    <div class="border-t border-border px-4 py-3">
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
        class="border-t border-border px-4 py-3"
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
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useStores } from '@/stores';
import { Button } from '@/components/ui';
import { BouncyToggle } from '@/components/custom/animation';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';
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

</script>
