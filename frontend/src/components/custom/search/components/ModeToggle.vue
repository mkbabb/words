<template>
    <div
        :class="[
            'flex flex-shrink-0 items-center justify-center overflow-hidden transition-all ease-out',
            `duration-${animationDuration}`
        ]"
        :style="{
            opacity: opacity,
            transform: `scale(${minScale + opacity * (maxScale - minScale)})`,
            pointerEvents: opacity > opacityThreshold ? 'auto' : 'none',
            width: opacity > opacityThreshold ? `${expandedWidth}px` : '0px',
            marginRight: opacity > opacityThreshold ? `${spacing}px` : '0px',
        }"
    >
        <FancyF
            :mode="modelValue"
            size="lg"
            :clickable="canToggle"
            :class="[
                'transition-colors duration-200',
                { 
                    'text-amber-950 dark:text-amber-300': aiMode,
                    'opacity-50 cursor-not-allowed': !canToggle,
                    'cursor-pointer hover:scale-110': canToggle
                }
            ]"
            @toggle-mode="handleToggle"
        />
    </div>
</template>

<script setup lang="ts">
import { FancyF } from '@/components/custom/icons';
import { useRouter } from 'vue-router';
import { useStores } from '@/stores';
import { useRouterSync } from '@/stores/composables/useRouterSync';
import { logger } from '@/utils/logger';
import type { LookupMode } from '@/types';

interface ModeToggleProps {
    canToggle: boolean;
    opacity: number;
    aiMode?: boolean;
    // Animation parameters
    minScale?: number;
    maxScale?: number;
    opacityThreshold?: number;
    expandedWidth?: number;
    spacing?: number;
    animationDuration?: number;
}

const props = withDefaults(defineProps<ModeToggleProps>(), {
    aiMode: false,
    minScale: 0.9,
    maxScale: 1.0,
    opacityThreshold: 0.1,
    expandedWidth: 48,
    spacing: 2,
    animationDuration: 300
});

// Using defineModel for two-way binding (modern Vue 3.4+) with centralized type
const modelValue = defineModel<LookupMode>({ required: true });

// Initialize router and stores at component level
const router = useRouter();
const { searchBar, content } = useStores();
const { navigateToLookupMode } = useRouterSync();

const handleToggle = async () => {
    if (!props.canToggle) return;

    // Safety checks
    if (!router) {
        logger.error('Router is not available in ModeToggle');
        return;
    }

    if (!searchBar) {
        logger.error('SearchBar store is not available in ModeToggle');
        return;
    }

    const current = modelValue.value;

    // Simple state machine with clear transitions using centralized types
    const transitions: Record<LookupMode, LookupMode> = {
        // From dictionary
        'dictionary': 'thesaurus',

        // From thesaurus
        'thesaurus': content.wordSuggestions ? 'suggestions' : 'dictionary',

        // From suggestions
        'suggestions': 'dictionary'
    };

    const newMode = transitions[current] || 'dictionary';
    modelValue.value = newMode;

    // Handle router navigation for definition/thesaurus/suggestions toggle
    if (searchBar.searchMode === 'lookup' && searchBar.searchQuery && searchBar.searchQuery.trim()) {
        const currentWord = searchBar.searchQuery;

        // Use the enhanced router navigation with router instance
        navigateToLookupMode(currentWord, newMode);
    }
};
</script>