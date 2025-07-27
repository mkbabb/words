import type { TransformedDefinition, CardVariant } from '@/types';
import type { Component } from 'vue';

export interface GroupedDefinition {
    clusterId: string;
    clusterDescription: string;
    definitions: TransformedDefinition[];
    maxRelevancy: number;
}

export interface ThemeOption {
    label: string;
    value: CardVariant;
}

export interface AnimationConfig {
    component: Component;
    props: Record<string, any>;
}

export interface DefinitionDisplayEmits {
    'toggle-pronunciation': [];
    'regenerate-examples': [definitionIndex: number];
    'synonym-click': [word: string];
    'theme-change': [theme: CardVariant];
}

export interface DefinitionSharedState {
    // Animation state
    animationKey: number;
    selectedAnimation: string;
    animationTimeout: NodeJS.Timeout | null;
    
    // UI state
    showThemeDropdown: boolean;
    showAnimationDropdown: boolean;
    regeneratingIndex: number | null;
    pronunciationMode: 'phonetic' | 'ipa';
    
    // Component mount state
    isMounted: boolean;
}

export type PartOfSpeechNavigation = {
    clusterId: string;
    partOfSpeech: string;
    key: string;
};