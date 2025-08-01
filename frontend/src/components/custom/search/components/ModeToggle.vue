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

// Initialize router and stores at component level
const router = useRouter();
const { searchConfig, searchBar, searchResults } = useStores();

const handleToggle = async () => {
    if (!props.canToggle) return;
    
    console.log('🔄 ModeToggle handleToggle called');
    
    // Safety checks
    if (!router) {
        console.error('❌ Router is not available in ModeToggle');
        return;
    }
    
    if (!searchConfig || !searchBar || !searchResults) {
        console.error('❌ Stores are not available in ModeToggle');
        return;
    }
    
    const current = modelValue.value;
    console.log('🔄 Current mode:', current);
    
    // Simple state machine with clear transitions
    const transitions: Record<string, 'dictionary' | 'thesaurus' | 'suggestions'> = {
        // From dictionary
        'dictionary': 'thesaurus',
        
        // From thesaurus
        'thesaurus': searchResults.wordSuggestions ? 'suggestions' : 'dictionary',
        
        // From suggestions
        'suggestions': 'dictionary'
    };
    
    const newMode = transitions[current] || 'dictionary';
    console.log('🔄 New mode:', newMode);
    modelValue.value = newMode;
    
    // Handle router navigation for definition/thesaurus toggle
    if (searchConfig.searchMode === 'lookup' && searchBar.searchQuery && searchBar.searchQuery.trim()) {
        const currentWord = searchBar.searchQuery;
        console.log('🧭 Navigation needed for word:', currentWord, 'to mode:', newMode);
        
        try {
            // Additional safety check for router
            if (!router || typeof router.push !== 'function') {
                console.error('❌ Router is not available or push method is missing');
                return;
            }
            
            if (newMode === 'thesaurus') {
                console.log('🧭 Navigating to thesaurus route');
                await router.push(`/thesaurus/${encodeURIComponent(currentWord)}`);
            } else if (newMode === 'dictionary') {
                console.log('🧭 Navigating to definition route');
                await router.push(`/definition/${encodeURIComponent(currentWord)}`);
            }
            // Note: suggestions mode stays on the same route as it's an overlay mode
            console.log('✅ Navigation completed successfully');
        } catch (error) {
            console.error('❌ Router navigation error in ModeToggle:', error);
            console.error('Router object:', router);
            console.error('NewMode:', newMode);
            console.error('CurrentWord:', currentWord);
        }
    } else {
        console.log('🔄 No navigation needed - not in lookup mode or no query');
    }
};
</script>