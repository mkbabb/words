import { computed, type ComputedRef } from 'vue';
import type { SynthesizedDictionaryEntry } from '@/types';

export function useProviders(entry: ComputedRef<SynthesizedDictionaryEntry | null>) {
    const usedProviders = computed(() => {
        if (!entry.value?.definitions) return [];
        
        const providers = new Set<string>();
        
        entry.value.definitions.forEach((def) => {
            if (def.source) {
                providers.add(def.source);
            }
        });
        
        return Array.from(providers);
    });

    return {
        usedProviders
    };
}