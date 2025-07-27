import { 
    AppleIcon,
    WiktionaryIcon, 
    OxfordIcon, 
    DictionaryIcon 
} from '@/components/custom/icons';
import { RefreshCw } from 'lucide-vue-next';
import type { Component } from 'vue';

export interface ProviderConfig {
    name: string;
    icon: Component;
    url: (word: string) => string;
}

export const PROVIDER_CONFIG: Record<string, ProviderConfig> = {
    wiktionary: {
        name: 'Wiktionary',
        icon: WiktionaryIcon,
        url: (word: string) => `https://en.wiktionary.org/wiki/${encodeURIComponent(word)}`,
    },
    oxford: {
        name: 'Oxford Dictionary',
        icon: OxfordIcon,
        url: (word: string) => `https://www.oxfordlearnersdictionaries.com/definition/english/${encodeURIComponent(word)}`,
    },
    dictionary_com: {
        name: 'Dictionary.com',
        icon: DictionaryIcon,
        url: (word: string) => `https://www.dictionary.com/browse/${encodeURIComponent(word)}`,
    },
    apple_dictionary: {
        name: 'Apple Dictionary',
        icon: AppleIcon,
        url: (word: string) => `dict://${encodeURIComponent(word)}`, // macOS Dictionary app URL scheme
    },
    ai_fallback: {
        name: 'AI Generated',
        icon: RefreshCw,
        url: () => '#', // No external URL for AI
    },
};