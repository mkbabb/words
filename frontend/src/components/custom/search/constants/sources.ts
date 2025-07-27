import {
    WiktionaryIcon,
    OxfordIcon,
    DictionaryIcon,
    AppleIcon,
} from '@/components/custom/icons';
import { Globe, Languages } from 'lucide-vue-next';
import type { SourceConfig, LanguageConfig } from '../types';

// Type safe sources configuration
export const DICTIONARY_SOURCES: SourceConfig[] = [
    { id: 'wiktionary', name: 'Wiktionary', icon: WiktionaryIcon },
    { id: 'oxford', name: 'Oxford', icon: OxfordIcon },
    { id: 'dictionary_com', name: 'Dictionary.com', icon: DictionaryIcon },
    { id: 'apple_dictionary', name: 'Apple Dictionary', icon: AppleIcon },
];

// Languages configuration with Lucide icons
export const LANGUAGES: LanguageConfig[] = [
    { value: 'en', label: 'EN', icon: Globe },
    { value: 'fr', label: 'FR', icon: Languages },
    { value: 'es', label: 'ES', icon: Languages },
    { value: 'de', label: 'DE', icon: Languages },
    { value: 'it', label: 'IT', icon: Languages },
];