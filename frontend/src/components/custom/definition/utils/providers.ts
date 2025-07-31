import type { Component } from 'vue';
import type { Definition } from '@/types/api';
import { PROVIDER_CONFIG } from '../constants/providers';
import { RefreshCw } from 'lucide-vue-next';

/**
 * Gets the display name for a provider
 */
export function getProviderDisplayName(provider: string): string {
    return PROVIDER_CONFIG[provider]?.name || provider;
}

/**
 * Gets the icon component for a provider
 */
export function getProviderIcon(provider: string): Component {
    return PROVIDER_CONFIG[provider]?.icon || RefreshCw;
}

/**
 * Gets the search URL for a provider and word
 */
export function getProviderSearchUrl(provider: string, word: string): string {
    return PROVIDER_CONFIG[provider]?.url(word) || '#';
}

/**
 * Extracts unique providers from definitions
 */
export function extractUniqueProviders(definitions: Array<Definition & { providers_data: any[] }>): string[] {
    if (!definitions) return [];
    
    const providers = new Set<string>();
    
    // Check providers_data array for each definition
    definitions.forEach((def) => {
        if (def.providers_data && Array.isArray(def.providers_data)) {
            def.providers_data.forEach((providerData: any) => {
                if (providerData.provider) {
                    providers.add(providerData.provider);
                }
            });
        }
    });
    
    return Array.from(providers);
}