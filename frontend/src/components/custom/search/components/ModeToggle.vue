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
import { useAppStore } from '@/stores';

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

// Using defineModel for two-way binding (modern Vue 3.4+)
const modelValue = defineModel<'dictionary' | 'thesaurus' | 'suggestions'>({ required: true });

const handleToggle = () => {
    if (!props.canToggle) return;
    
    const store = useAppStore();
    const router = useRouter();
    const current = modelValue.value;
    
    // Simple state machine with clear transitions
    const transitions: Record<string, 'dictionary' | 'thesaurus' | 'suggestions'> = {
        // From dictionary
        'dictionary': 'thesaurus',
        
        // From thesaurus
        'thesaurus': store.wordSuggestions ? 'suggestions' : 'dictionary',
        
        // From suggestions
        'suggestions': 'dictionary'
    };
    
    const newMode = transitions[current] || 'dictionary';
    modelValue.value = newMode;
    
    // Handle router navigation for definition/thesaurus toggle
    if (store.searchMode === 'lookup' && store.searchQuery && store.searchQuery.trim()) {
        const currentWord = store.searchQuery;
        try {
            if (newMode === 'thesaurus') {
                router.push(`/thesaurus/${encodeURIComponent(currentWord)}`);
            } else if (newMode === 'dictionary') {
                router.push(`/definition/${encodeURIComponent(currentWord)}`);
            }
            // Note: suggestions mode stays on the same route as it's an overlay mode
        } catch (error) {
            console.error('Router navigation error in ModeToggle:', error);
        }
    }
};
</script>