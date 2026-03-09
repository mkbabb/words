<template>
    <div class="space-y-0">
        <Accordion 
            type="multiple" 
            v-model="accordionValue"
            :collapsible="true"
        >
            <!-- Recent Lookups -->
            <SidebarSection
                value="recent"
                title="Recent Lookups"
                :items="recentLookups"
                :empty-message="'No recent lookups'"
            >
                <template #item="{ item }">
                    <SidebarRecentItem
                        :item="item"
                        :title="item.word"
                        :subtitle="getFirstDefinition(item)"
                        :timestamp="item.timestamp"
                        @click="handleLookupClick(item)"
                    />
                </template>
            </SidebarSection>

            <!-- AI Query History -->
            <SidebarSection
                value="ai-queries"
                title="AI Queries"
                :items="recentAISuggestions"
                :empty-message="'No AI queries yet'"
            >
                <template #item="{ item }">
                    <button
                        class="flex w-full items-start gap-3 rounded px-3 py-2.5 hover:bg-muted/50 text-left"
                        @click="handleAISuggestionClick(item)"
                    >
                        <Sparkles class="mt-0.5 h-3.5 w-3.5 text-amber-500 dark:text-amber-400 flex-shrink-0" />
                        <div class="flex-1 min-w-0">
                            <p class="text-xs leading-relaxed text-foreground/90 line-clamp-2">
                                {{ item.query }}
                            </p>
                        </div>
                    </button>
                </template>
            </SidebarSection>

            <!-- Vocabulary Suggestions -->
            <GoldenSidebarSection
                value="vocabulary"
                title="Vocabulary Building"
                :items="vocabularySuggestions"
                :empty-message="'Look up words to get personalized suggestions'"
            >
                <template #item="{ item }">
                    <VocabularySuggestionItem
                        :suggestion="item"
                        @click="handleSuggestionClick(item)"
                    />
                </template>
            </GoldenSidebarSection>

            <!-- Recent Searches -->
            <SidebarSection
                value="searches"
                title="Recent Searches"
                :items="recentSearches"
                :empty-message="'No recent searches'"
            >
                <template #item="{ item }">
                    <button
                        class="flex w-full items-start gap-3 rounded px-3 py-2.5 hover:bg-muted/50 text-left"
                        @click="handleSearchClick(item)"
                    >
                        <Search class="mt-0.5 h-3.5 w-3.5 text-foreground/40 flex-shrink-0" />
                        <div class="flex-1 min-w-0">
                            <p class="text-xs text-foreground/70">{{ item.query }}</p>
                        </div>
                    </button>
                </template>
            </SidebarSection>
        </Accordion>
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useStores } from '@/stores';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';
import { useRouter } from 'vue-router';
import { Accordion } from '@/components/ui/accordion';
import { Search, Sparkles } from 'lucide-vue-next';
import SidebarSection from './SidebarSection.vue';
import GoldenSidebarSection from './GoldenSidebarSection.vue';
import SidebarRecentItem from './SidebarRecentItem.vue';
import VocabularySuggestionItem from './VocabularySuggestionItem.vue';
import type { SynthesizedDictionaryEntry } from '@/types';
import { logger } from '@/utils/logger';

const { history, ui, content } = useStores();
const searchBar = useSearchBarStore();
const router = useRouter();
const { recentLookups, vocabularySuggestions, recentSearches, aiQueryHistory } = storeToRefs(history);

// Create orchestrator for API operations
const orchestrator = useSearchOrchestrator({
    query: computed(() => searchBar.searchQuery)
});

// Computed property to format AI query history for display
const recentAISuggestions = computed(() => 
    aiQueryHistory.value.map(item => ({
        query: item.query,
        timestamp: new Date(item.timestamp)
    }))
);

// Accordion state management - default to collapsed (empty array)
const accordionValue = computed({
    get: () => (content.sidebarAccordionState.lookup || []) as string[],
    set: (value) => {
        content.setSidebarAccordionState('lookup', value as string[]);
    }
});

const getFirstDefinition = (entry: SynthesizedDictionaryEntry): string => {
    const firstDef = entry.definitions?.[0];
    if (!firstDef) return '';
    
    const text = firstDef.text || '';
    return text.length > 60 ? text.substring(0, 60) + '...' : text;
};

const handleLookupClick = async (lookup: SynthesizedDictionaryEntry) => {
    searchBar.setQuery(lookup.word);

    // Navigate to appropriate route based on mode — route watcher handles the fetch
    const subMode = searchBar.getSubMode('lookup');
    const routeName = subMode === 'thesaurus' ? 'Thesaurus' : 'Definition';
    router.push({ name: routeName, params: { word: lookup.word } });

    // Close mobile sidebar if open
    if (ui.sidebarOpen) {
        ui.toggleSidebar();
    }
};

const handleSuggestionClick = async (suggestion: { word: string }) => {
    searchBar.setQuery(suggestion.word);

    // Use modern mode system - just change the modes
    searchBar.setMode('lookup');
    searchBar.setSubMode('lookup', 'dictionary');

    // Navigate to Definition route — route watcher handles the fetch
    router.push({ name: 'Definition', params: { word: suggestion.word } });

    // Close mobile sidebar if open
    if (ui.sidebarOpen) {
        ui.toggleSidebar();
    }
};


const handleSearchClick = async (search: { query: string }) => {
    // Navigate to appropriate route based on mode — route watcher handles the fetch
    const subMode = searchBar.getSubMode('lookup');
    const routeName = subMode === 'thesaurus' ? 'Thesaurus' : 'Definition';
    router.push({ name: routeName, params: { word: search.query } });

    // Close mobile sidebar if open
    if (ui.sidebarOpen) {
        ui.toggleSidebar();
    }
};

const handleAISuggestionClick = async (suggestion: { query: string }) => {
    // Use modern mode system - just change the modes
    searchBar.setMode('lookup');
    searchBar.setSubMode('lookup', 'suggestions');
    
    // Navigate to home to display suggestions
    router.push({ name: 'Home' });
    
    // Trigger AI suggestions search (will set isDirectLookup flag)
    try {
        // Extract word count from the query (default to 12)
        const wordCount = extractWordCount(suggestion.query);
        const results = await orchestrator.getAISuggestions(suggestion.query, wordCount);
        
        if (results && results.suggestions.length > 0) {
            // Set searchQuery after successful AI suggestions to avoid triggering search
            searchBar.setQuery(suggestion.query);
        }
    } catch (error) {
        logger.error('Error getting AI suggestions:', error);
    }
    
    // Close mobile sidebar if open
    if (ui.sidebarOpen) {
        ui.toggleSidebar();
    }
};

// Helper function to extract word count from query
const extractWordCount = (query: string): number => {
    const match = query.match(/(\d+)\s*words?/i);
    return match ? parseInt(match[1], 10) : 12;
};

// Initialize vocabulary suggestions on component mount
onMounted(async () => {
    if (history.vocabularySuggestions.length === 0 && history.recentLookups.length > 0) {
        try {
            await history.refreshVocabularySuggestions();
        } catch (error) {
            logger.error('Failed to generate vocabulary suggestions:', error);
        }
    }
});
</script>