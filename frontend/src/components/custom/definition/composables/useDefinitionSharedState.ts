import { reactive, computed } from 'vue';
import type { DefinitionSharedState } from '../types';

// Modern Vue 3 pattern - shared state that persists across component instances
const state = reactive<DefinitionSharedState>({
    // Animation state
    animationKey: 0,
    selectedAnimation: 'typewriter',
    animationTimeout: null,
    
    // UI state
    showThemeDropdown: false,
    showAnimationDropdown: false,
    regeneratingIndex: null,
    pronunciationMode: 'phonetic',
    
    // Component mount state
    isMounted: false,
});

// Animation control functions
const scheduleNextAnimation = (delayMs: number) => {
    if (state.animationTimeout) {
        clearTimeout(state.animationTimeout);
    }
    
    state.animationTimeout = setTimeout(() => {
        state.animationKey++;
        // Schedule next animation with random delay between 60-90 seconds
        const nextDelay = 60000 + Math.random() * 30000;
        scheduleNextAnimation(nextDelay);
    }, delayMs);
};

const startAnimationCycle = () => {
    // Initial delay of 15 seconds
    scheduleNextAnimation(15000);
};

const stopAnimationCycle = () => {
    if (state.animationTimeout) {
        clearTimeout(state.animationTimeout);
        state.animationTimeout = null;
    }
};

// Pronunciation toggle
const togglePronunciation = () => {
    state.pronunciationMode = state.pronunciationMode === 'phonetic' ? 'ipa' : 'phonetic';
};

// Regenerate examples
const setRegeneratingIndex = (index: number | null) => {
    state.regeneratingIndex = index;
};

// Theme dropdown
const toggleThemeDropdown = () => {
    state.showThemeDropdown = !state.showThemeDropdown;
    // Close animation dropdown if open
    if (state.showThemeDropdown) {
        state.showAnimationDropdown = false;
    }
};

const closeDropdowns = () => {
    state.showThemeDropdown = false;
    state.showAnimationDropdown = false;
};

// Export the shared state and control functions
export function useDefinitionSharedState() {
    return {
        state,
        
        // Animation controls
        startAnimationCycle,
        stopAnimationCycle,
        
        // UI controls
        togglePronunciation,
        setRegeneratingIndex,
        toggleThemeDropdown,
        closeDropdowns,
        
        // Computed
        isRegenerating: computed(() => state.regeneratingIndex !== null),
    };
}