/**
 * Validates persisted Pinia store state on hydration.
 * Ensures stale/invalid values from localStorage don't cause runtime errors.
 */
import {
    isValidDictionarySource,
    isValidLanguage,
    isValidCardVariant,
    isValidPronunciationMode,
    isValidViewMode,
    DEFAULT_SOURCES,
    DEFAULT_LANGUAGES,
    DEFAULT_CARD_VARIANT,
    DEFAULT_PRONUNCIATION_MODE,
    DEFAULT_VIEW_MODE,
    type DictionarySource,
    type Language,
} from '@/stores/types/constants';
import { isSearchMode, isLookupMode } from '@/types/modes';
import { logger } from '@/utils/logger';

type StoreContext = {
    store: any;
};

export function validatePersistedState(ctx: StoreContext): void {
    const { store } = ctx;

    try {
        switch (store.$id) {
            case 'searchBar':
                validateSearchBar(store);
                break;
            case 'lookupMode':
                validateLookupMode(store);
                break;
            case 'wordlistMode':
                validateWordlistMode(store);
                break;
        }
    } catch (e) {
        logger.error(`Failed to validate persisted state for ${store.$id}:`, e);
    }
}

function validateSearchBar(store: any): void {
    // Validate searchMode
    if (!isSearchMode(store.searchMode)) {
        logger.warn(`Invalid persisted searchMode "${store.searchMode}", resetting to "lookup"`);
        store.searchMode = 'lookup';
    }

    // Validate previousMode
    if (!isSearchMode(store.previousMode)) {
        store.previousMode = 'lookup';
    }

    // Validate searchSubMode values
    if (store.searchSubMode && typeof store.searchSubMode === 'object') {
        // Validate lookup submode
        if (store.searchSubMode.lookup && !isLookupMode(store.searchSubMode.lookup)) {
            logger.warn(`Invalid persisted lookup subMode "${store.searchSubMode.lookup}", resetting to "dictionary"`);
            store.searchSubMode = { ...store.searchSubMode, lookup: 'dictionary' };
        }

        // Validate wordlist submode
        const validWordlistSubModes = ['all', 'filtered', 'search'];
        if (store.searchSubMode.wordlist && !validWordlistSubModes.includes(store.searchSubMode.wordlist)) {
            store.searchSubMode = { ...store.searchSubMode, wordlist: 'all' };
        }

        // Validate word-of-the-day submode
        const validWotdSubModes = ['current', 'archive'];
        if (store.searchSubMode['word-of-the-day'] && !validWotdSubModes.includes(store.searchSubMode['word-of-the-day'])) {
            store.searchSubMode = { ...store.searchSubMode, 'word-of-the-day': 'current' };
        }

        // Validate stage submode
        const validStageSubModes = ['test', 'debug'];
        if (store.searchSubMode.stage && !validStageSubModes.includes(store.searchSubMode.stage)) {
            store.searchSubMode = { ...store.searchSubMode, stage: 'test' };
        }
    }
}

function validateLookupMode(store: any): void {
    // Validate selectedSources — filter to only valid enum values
    if (Array.isArray(store.selectedSources)) {
        const validSources = store.selectedSources.filter(
            (s: string) => isValidDictionarySource(s)
        ) as DictionarySource[];
        if (validSources.length === 0) {
            logger.warn('No valid persisted sources, resetting to defaults');
            store.selectedSources = [...DEFAULT_SOURCES];
        } else if (validSources.length !== store.selectedSources.length) {
            logger.warn('Filtered invalid persisted sources');
            store.selectedSources = validSources;
        }
    } else {
        store.selectedSources = [...DEFAULT_SOURCES];
    }

    // Validate selectedLanguages
    if (Array.isArray(store.selectedLanguages)) {
        const validLangs = store.selectedLanguages.filter(
            (l: string) => isValidLanguage(l)
        ) as Language[];
        if (validLangs.length === 0) {
            logger.warn('No valid persisted languages, resetting to defaults');
            store.selectedLanguages = [...DEFAULT_LANGUAGES];
        } else if (validLangs.length !== store.selectedLanguages.length) {
            logger.warn('Filtered invalid persisted languages');
            store.selectedLanguages = validLangs;
        }
    } else {
        store.selectedLanguages = [...DEFAULT_LANGUAGES];
    }

    // Validate selectedCardVariant
    if (!isValidCardVariant(store.selectedCardVariant)) {
        store.selectedCardVariant = DEFAULT_CARD_VARIANT;
    }

    // Validate pronunciationMode
    if (!isValidPronunciationMode(store.pronunciationMode)) {
        store.pronunciationMode = DEFAULT_PRONUNCIATION_MODE;
    }

    // Validate searchMode (SearchMethod[])
    const validSearchMethods = ['smart', 'exact', 'fuzzy', 'semantic'];
    if (Array.isArray(store.searchMode)) {
        const valid = store.searchMode.filter((m: string) => validSearchMethods.includes(m));
        if (valid.length === 0) {
            store.searchMode = ['smart'];
        } else if (valid.length !== store.searchMode.length) {
            store.searchMode = valid;
        }
    } else {
        store.searchMode = ['smart'];
    }
}

function validateWordlistMode(store: any): void {
    // Validate viewMode
    if (!isValidViewMode(store.viewMode)) {
        store.viewMode = DEFAULT_VIEW_MODE;
    }

    // selectedWordlist is a UUID string or null — we can't validate existence
    // without an API call, so we just ensure it's a string or null
    if (store.selectedWordlist !== null && typeof store.selectedWordlist !== 'string') {
        store.selectedWordlist = null;
    }

    // Validate itemsPerPage is a reasonable number
    if (typeof store.itemsPerPage !== 'number' || store.itemsPerPage < 1 || store.itemsPerPage > 200) {
        store.itemsPerPage = 25;
    }
}
