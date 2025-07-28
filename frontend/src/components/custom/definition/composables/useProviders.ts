import { computed, type ComputedRef } from 'vue';
import type { SynthesizedDictionaryEntry } from '@/types';

export function useProviders(entry: ComputedRef<SynthesizedDictionaryEntry | null>) {
    const usedProviders = computed(() => {
        if (!entry.value?.definitions) return [];
        
        const providers = new Set<string>();
        
        entry.value.definitions.forEach((def) => {
            // Check providers_data array for each definition
            if (def.providers_data && Array.isArray(def.providers_data)) {
                def.providers_data.forEach((providerData: any) => {
                    if (providerData.provider) {
                        providers.add(providerData.provider);
                    }
                });
            }
            // Fallback to source if providers_data is not available
            else if (def.source) {
                providers.add(def.source);
            }
        });
        
        return Array.from(providers);
    });

    return {
        usedProviders
    };
}