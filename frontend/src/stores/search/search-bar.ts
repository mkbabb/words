import { defineStore } from 'pinia';
import { ref, readonly, computed } from 'vue';
import { useLookupMode } from './modes/lookup';
import { useWordlistMode } from './modes/wordlist';
import type { SearchMode, SearchSubMode, SearchSubModeMap } from '@/types';

/**
 * Unified SearchBarStore - State management only
 * Handles search input, mode management, and results delegation
 */
export const useSearchBarStore = defineStore(
    'searchBar',
    () => {
        // ==========================================================================
        // CORE MODE STATE
        // ==========================================================================
        
        const searchMode = ref<SearchMode>('lookup');
        const previousMode = ref<SearchMode>('lookup');
        
        const searchSubMode = ref<Record<SearchMode, SearchSubMode<SearchMode>>>({
            lookup: 'dictionary',
            wordlist: 'all',
            'word-of-the-day': 'current',
            stage: 'test'
        });
        
        // Query persistence across modes
        const savedQueries = ref<Record<SearchMode, string>>({
            'lookup': '',
            'wordlist': '',
            'word-of-the-day': '',
            'stage': ''
        });

        // ==========================================================================
        // SHARED SEARCH BAR STATE
        // ==========================================================================

        const searchQuery = ref('');
        const searchSelectedIndex = ref(0);
        const showDropdown = ref(false);
        const showSearchControls = ref(false);
        const isFocused = ref(false);
        const isHovered = ref(false);
        const hasErrorAnimation = ref(false);
        const modeSwitchAnimation = ref(false);
        const isDirectLookup = ref(false);
        const autocompleteText = ref('');

        // ==========================================================================
        // MODE-SPECIFIC STORES
        // ==========================================================================

        const lookupMode = useLookupMode();
        const wordlistMode = useWordlistMode();

        // Mode store registry
        const modeStores = {
            lookup: lookupMode,
            wordlist: wordlistMode,
            'word-of-the-day': null,
            stage: null
        } as const;

        // ==========================================================================
        // COMPUTED PROPERTIES
        // ==========================================================================

        const currentMode = computed(() => searchMode.value);
        
        // Get current mode's store
        const currentModeStore = computed(() => {
            return modeStores[currentMode.value];
        });
        
        // Unified results access
        const currentResults = computed(() => {
            switch (searchMode.value) {
                case 'lookup':
                    return lookupMode.results;
                case 'wordlist':
                    return wordlistMode.results;
                default:
                    return [];
            }
        });
        
        const hasResults = computed(() => currentResults.value.length > 0);
        
        // Mode-specific properties
        const isAIQuery = computed(() =>
            currentMode.value === 'lookup' ? lookupMode.isAIQuery : false
        );

        const showSparkle = computed(() =>
            currentMode.value === 'lookup' ? lookupMode.showSparkle : false
        );

        const aiSuggestions = computed(() =>
            currentMode.value === 'lookup' ? lookupMode.aiSuggestions : []
        );

        const batchMode = computed(() =>
            currentMode.value === 'wordlist' ? wordlistMode.batchMode : false
        );

        const processingQueue = computed(() =>
            currentMode.value === 'wordlist' ? wordlistMode.processingQueue : []
        );

        // ==========================================================================
        // MODE MANAGEMENT
        // ==========================================================================
        
        const setMode = async (newMode: SearchMode, currentQuery?: string) => {
            if (newMode !== searchMode.value) {
                console.log('🔄 Mode change:', searchMode.value, '->', newMode);
                
                // Save current query if provided
                if (currentQuery !== undefined) {
                    saveCurrentQuery(currentQuery);
                }
                
                // Execute exit handler for previous mode
                const previousModeStore = modeStores[searchMode.value];
                if (previousModeStore?.handler?.onExit) {
                    await previousModeStore.handler.onExit(newMode);
                }
                
                // Update mode
                previousMode.value = searchMode.value;
                searchMode.value = newMode;
                
                // Execute enter handler for new mode
                const newModeStore = modeStores[newMode];
                if (newModeStore?.handler?.onEnter) {
                    await newModeStore.handler.onEnter(previousMode.value);
                }
                
                // Trigger mode switch animation
                triggerModeSwitchAnimation();
                
                console.log('✅ Mode changed to:', newMode);
                
                // Return saved query for the new mode
                return getSavedQuery(newMode);
            }
            return '';
        };
        
        const setSubMode = <T extends SearchMode>(mode: T, newSubMode: SearchSubModeMap[T]) => {
            const currentSubMode = searchSubMode.value[mode];
            if (newSubMode !== currentSubMode) {
                console.log(`🔄 ${mode} sub-mode change:`, currentSubMode, '->', newSubMode);
                
                searchSubMode.value = {
                    ...searchSubMode.value,
                    [mode]: newSubMode
                };
                console.log(`✅ ${mode} sub-mode changed to:`, newSubMode);
            }
        };
        
        const getSubMode = <T extends SearchMode>(mode: T): SearchSubModeMap[T] => {
            return searchSubMode.value[mode] as SearchSubModeMap[T];
        };
        
        const toggleSearchMode = () => {
            const modes: SearchMode[] = ['lookup', 'wordlist', 'word-of-the-day', 'stage'];
            const currentIndex = modes.indexOf(searchMode.value);
            const nextIndex = (currentIndex + 1) % modes.length;
            setMode(modes[nextIndex]);
        };

        // ==========================================================================
        // QUERY MANAGEMENT
        // ==========================================================================
        
        const saveCurrentQuery = (query: string) => {
            savedQueries.value[searchMode.value] = query;
            console.log('💾 Saved query for', searchMode.value, ':', query);
        };
        
        const getSavedQuery = (mode: SearchMode) => {
            return savedQueries.value[mode] || '';
        };
        
        const getPreviousMode = () => previousMode.value;

        // ==========================================================================
        // SHARED ACTIONS
        // ==========================================================================

        const setQuery = (query: string) => {
            searchQuery.value = query;
        };

        const clearQuery = () => {
            searchQuery.value = '';
            searchSelectedIndex.value = 0;
        };

        const setSelectedIndex = (index: number) => {
            searchSelectedIndex.value = index;
        };

        const toggleDropdown = () => {
            showDropdown.value = !showDropdown.value;
        };

        const setDropdown = (show: boolean) => {
            showDropdown.value = show;
        };

        const openDropdown = () => {
            showDropdown.value = true;
        };

        const hideDropdown = () => {
            showDropdown.value = false;
        };

        const toggleSearchControls = () => {
            showSearchControls.value = !showSearchControls.value;
        };

        const setSearchControls = (show: boolean) => {
            showSearchControls.value = show;
        };

        const setFocused = (focused: boolean) => {
            isFocused.value = focused;
            if (!focused) {
                showDropdown.value = false;
            }
        };

        const setHovered = (hovered: boolean) => {
            isHovered.value = hovered;
        };

        const setDirectLookup = (directLookup: boolean) => {
            isDirectLookup.value = directLookup;
        };

        const setAutocompleteText = (text: string) => {
            autocompleteText.value = text;
        };

        const hideControls = () => {
            showSearchControls.value = false;
        };

        const resetSelection = () => {
            searchSelectedIndex.value = 0;
        };

        const triggerErrorAnimation = () => {
            hasErrorAnimation.value = true;
            setTimeout(() => {
                hasErrorAnimation.value = false;
            }, 600);
        };

        const triggerModeSwitchAnimation = () => {
            modeSwitchAnimation.value = true;
            setTimeout(() => {
                modeSwitchAnimation.value = false;
            }, 400);
        };
        
        // ==========================================================================
        // RESULTS MANAGEMENT
        // ==========================================================================
        
        const clearResults = () => {
            const store = currentModeStore.value;
            if (store) {
                store.clearResults();
            }
        };
        
        const getResults = <T extends SearchMode>(mode?: T) => {
            const targetMode = mode || searchMode.value;
            const store = modeStores[targetMode];
            return store?.results || [];
        };

        // ==========================================================================
        // MODE-SPECIFIC ACTION DELEGATES
        // ==========================================================================

        // Lookup mode actions
        const setAIQuery = (isAI: boolean) => {
            if (currentMode.value === 'lookup') {
                lookupMode.setAIQuery(isAI);
            }
        };

        const setShowSparkle = (show: boolean) => {
            if (currentMode.value === 'lookup') {
                lookupMode.setShowSparkle(show);
            }
        };

        const setAISuggestions = (suggestions: string[]) => {
            if (currentMode.value === 'lookup') {
                lookupMode.setAISuggestions(suggestions);
            }
        };

        const addAISuggestion = (suggestion: string) => {
            if (currentMode.value === 'lookup') {
                lookupMode.addAISuggestion(suggestion);
            }
        };

        const clearAISuggestions = () => {
            if (currentMode.value === 'lookup') {
                lookupMode.clearAISuggestions();
            }
        };

        // Wordlist mode actions
        const toggleBatchMode = () => {
            if (currentMode.value === 'wordlist') {
                wordlistMode.toggleBatchMode();
            }
        };

        const setBatchMode = (enabled: boolean) => {
            if (currentMode.value === 'wordlist') {
                wordlistMode.setBatchMode(enabled);
            }
        };

        const addToQueue = (word: string) => {
            if (currentMode.value === 'wordlist') {
                wordlistMode.addToQueue(word);
            }
        };

        const addBatchToQueue = (words: string[]) => {
            if (currentMode.value === 'wordlist') {
                wordlistMode.addBatchToQueue(words);
            }
        };

        const removeFromQueue = (word: string) => {
            if (currentMode.value === 'wordlist') {
                wordlistMode.removeFromQueue(word);
            }
        };

        const clearQueue = () => {
            if (currentMode.value === 'wordlist') {
                wordlistMode.clearQueue();
            }
        };

        // ==========================================================================
        // RESET
        // ==========================================================================

        const reset = () => {
            // Reset mode state
            searchMode.value = 'lookup';
            previousMode.value = 'lookup';
            searchSubMode.value = {
                lookup: 'dictionary',
                wordlist: 'all',
                'word-of-the-day': 'current',
                stage: 'test'
            };
            
            // Clear saved queries
            savedQueries.value = {
                'lookup': '',
                'wordlist': '',
                'word-of-the-day': '',
                'stage': ''
            };
            
            // Reset shared state
            searchQuery.value = '';
            searchSelectedIndex.value = 0;
            showDropdown.value = false;
            showSearchControls.value = false;
            isFocused.value = false;
            isHovered.value = false;
            hasErrorAnimation.value = false;
            modeSwitchAnimation.value = false;
            isDirectLookup.value = false;
            autocompleteText.value = '';

            // Reset mode-specific stores
            lookupMode.reset();
            wordlistMode.reset();
        };

        // ==========================================================================
        // RETURN API
        // ==========================================================================

        return {
            // Core Mode State
            searchMode: readonly(searchMode),
            searchSubMode: readonly(searchSubMode),
            previousMode: readonly(previousMode),
            savedQueries: readonly(savedQueries),
            
            // Shared State
            searchQuery: readonly(searchQuery),
            searchSelectedIndex: readonly(searchSelectedIndex),
            showDropdown: readonly(showDropdown),
            showSearchControls: readonly(showSearchControls),
            isFocused: readonly(isFocused),
            isHovered: readonly(isHovered),
            hasErrorAnimation: readonly(hasErrorAnimation),
            modeSwitchAnimation: readonly(modeSwitchAnimation),
            isDirectLookup: readonly(isDirectLookup),
            autocompleteText: readonly(autocompleteText),
            
            // Results State
            currentResults: readonly(currentResults),
            hasResults,

            // Mode-Specific State (computed)
            isAIQuery: readonly(isAIQuery),
            showSparkle: readonly(showSparkle),
            aiSuggestions: readonly(aiSuggestions),
            batchMode: readonly(batchMode),
            processingQueue: readonly(processingQueue),

            // Mode Management Actions
            setMode,
            setSubMode,
            getSubMode,
            toggleSearchMode,
            getPreviousMode,
            saveCurrentQuery,
            getSavedQuery,
            
            // Shared Actions
            setQuery,
            clearQuery,
            setSelectedIndex,
            toggleDropdown,
            setDropdown,
            toggleSearchControls,
            setSearchControls,
            setFocused,
            setHovered,
            setDirectLookup,
            setAutocompleteText,
            hideControls,
            resetSelection,
            openDropdown,
            hideDropdown,
            triggerErrorAnimation,
            triggerModeSwitchAnimation,
            
            // Results Management
            clearResults,
            getResults,

            // Mode-Specific Actions
            // Lookup
            setAIQuery,
            setShowSparkle,
            setAISuggestions,
            addAISuggestion,
            clearAISuggestions,

            // Wordlist
            toggleBatchMode,
            setBatchMode,
            addToQueue,
            addBatchToQueue,
            removeFromQueue,
            clearQueue,
            
            // Reset
            reset,

            // Direct mode store access
            lookupMode,
            wordlistMode,
            currentMode,
            currentModeStore,
        };
    },
    {
        persist: {
            key: 'search-bar',
            pick: [
                'searchMode',
                'searchSubMode',
                'previousMode',
                'savedQueries',
                'searchQuery',
                'showSearchControls',
            ],
        },
    }
);