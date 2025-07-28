<template>
    <div class="space-y-4">
        <!-- AI Vocabulary Suggestions (at the top) -->
        <div v-if="vocabularySuggestions.length > 0" class="space-y-3">
            <h3 class="text-muted-foreground text-sm font-medium">
                Vocabulary Suggestions
            </h3>
            <div class="space-y-2">
                <VocabularySuggestionItem
                    v-for="suggestion in vocabularySuggestions.slice(0, 3)"
                    :key="suggestion.word"
                    :suggestion="suggestion"
                    @click="handleSuggestionClick"
                />
            </div>
        </div>

        <!-- Gradient separator -->
        <hr v-if="vocabularySuggestions.length > 0" class="border-0 h-px bg-gradient-to-r from-transparent via-muted-foreground/20 to-transparent dark:via-muted-foreground/30" />

        <!-- Accordion for other sections -->
        <Accordion 
            type="multiple" 
            v-model="accordionValue"
            class="w-full"
        >
            <!-- Recent AI Suggestions -->
            <GoldenSidebarSection
                v-if="recentAISuggestions.length > 0"
                title="AI Suggestions"
                value="ai-suggestions"
                :items="recentAISuggestions"
                :count="recentAISuggestions.length"
                :icon="Wand2"
                empty-message="No recent AI suggestions"
            >
                <template #default="{ items }">
                    <SidebarRecentItem
                        v-for="suggestion in items"
                        :key="`${suggestion.query}-${suggestion.timestamp}`"
                        :item="suggestion"
                        :title="suggestion.query"
                        :timestamp="suggestion.timestamp"
                        @click="handleAISuggestionClick"
                    />
                </template>
            </GoldenSidebarSection>

            <!-- Gradient separator -->
            <hr v-if="recentAISuggestions.length > 0" class="my-2 border-0 h-px bg-gradient-to-r from-transparent via-yellow-400/20 to-transparent dark:via-yellow-400/30" />

            <!-- Recent Lookups -->
            <SidebarSection
                title="Lookups"
                value="lookups"
                :items="recentLookups"
                :count="recentLookups.length"
                :icon="Book"
                empty-message="No recent lookups"
            >
                <template #default="{ items }">
                    <SidebarRecentItem
                        v-for="lookup in items"
                        :key="lookup.word"
                        :item="lookup"
                        :title="lookup.word"
                        :subtitle="getFirstDefinition(lookup)"
                        :timestamp="lookup.timestamp"
                        @click="handleLookupClick"
                    />
                </template>
            </SidebarSection>

            <!-- Gradient separator -->
            <hr class="my-2 border-0 h-px bg-gradient-to-r from-transparent via-muted-foreground/20 to-transparent dark:via-muted-foreground/30" />

            <!-- Recent Searches -->
            <SidebarSection
                title="Searches"
                value="searches"
                :items="recentSearches"
                :count="recentSearches.length"
                :icon="Search"
                empty-message="No recent searches"
            >
                <template #default="{ items }">
                    <SidebarRecentItem
                        v-for="search in items"
                        :key="`${search.query}-${search.timestamp}`"
                        :item="search"
                        :title="search.query"
                        :subtitle="search.mode ? `${capitalizeFirst(search.mode)} search` : undefined"
                        :timestamp="search.timestamp"
                        @click="handleSearchClick"
                    />
                </template>
            </SidebarSection>
        </Accordion>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useAppStore } from '@/stores';
import { Accordion } from '@/components/ui/accordion';
import { Book, Search, Wand2 } from 'lucide-vue-next';
import { capitalizeFirst } from '@/utils';
import SidebarSection from './SidebarSection.vue';
import GoldenSidebarSection from './GoldenSidebarSection.vue';
import SidebarRecentItem from './SidebarRecentItem.vue';
import VocabularySuggestionItem from './VocabularySuggestionItem.vue';
import type { SynthesizedDictionaryEntry } from '@/types';

const store = useAppStore();
const { recentLookups, vocabularySuggestions, recentSearches, aiQueryHistory } = storeToRefs(store);

// Computed property to format AI query history for display
const recentAISuggestions = computed(() => 
    aiQueryHistory.value.map(item => ({
        query: item.query,
        timestamp: new Date(item.timestamp)
    }))
);

// Accordion state management - default to collapsed (empty array)
const accordionValue = computed({
    get: () => store.sidebarAccordionState.lookup || [],
    set: (value) => {
        store.sidebarAccordionState = {
            ...store.sidebarAccordionState,
            lookup: value as string[]
        };
    }
});

const getFirstDefinition = (entry: SynthesizedDictionaryEntry): string => {
    const firstDef = entry.definitions?.[0];
    if (!firstDef) return '';
    
    const text = firstDef.definition || firstDef.text || '';
    return text.length > 60 ? text.substring(0, 60) + '...' : text;
};

const handleLookupClick = async (lookup: SynthesizedDictionaryEntry) => {
    store.searchQuery = lookup.word;
    await store.searchWord(lookup.word);
    // Close mobile sidebar if open
    if (store.sidebarOpen) {
        store.toggleSidebar();
    }
};

const handleSuggestionClick = async (suggestion: { word: string }) => {
    store.searchQuery = suggestion.word;
    await store.searchWord(suggestion.word);
    // Close mobile sidebar if open
    if (store.sidebarOpen) {
        store.toggleSidebar();
    }
};


const handleSearchClick = (search: { query: string }) => {
    // Set the search query
    store.searchQuery = search.query;
    
    // If there's a current entry that matches this query, ensure it's set
    if (store.currentEntry && store.currentEntry.word.toLowerCase() === search.query.toLowerCase()) {
        // Current entry already matches
    } else {
        // Check if we have this word in recent lookups
        const matchingLookup = recentLookups.value.find(
            lookup => lookup.word.toLowerCase() === search.query.toLowerCase()
        );
        if (matchingLookup) {
            store.currentEntry = matchingLookup.entry;
        }
    }
    
    // Close mobile sidebar if open
    if (store.sidebarOpen) {
        store.toggleSidebar();
    }
};

const handleAISuggestionClick = async (suggestion: { query: string }) => {
    // Set query and enable AI mode
    store.searchQuery = suggestion.query;
    store.sessionState.isAIQuery = true;
    store.sessionState.aiQueryText = suggestion.query;
    store.mode = 'suggestions';
    
    // Trigger AI suggestions search
    try {
        // Extract word count from the query (default to 12)
        const wordCount = extractWordCount(suggestion.query);
        const results = await store.getAISuggestions(suggestion.query, wordCount);
        
        if (results && results.suggestions.length > 0) {
            store.wordSuggestions = results;
            store.hasSearched = true;
        }
    } catch (error) {
        console.error('Error getting AI suggestions:', error);
    }
    
    // Close mobile sidebar if open
    if (store.sidebarOpen) {
        store.toggleSidebar();
    }
};

// Helper function to extract word count from query
const extractWordCount = (query: string): number => {
    const match = query.match(/(\d+)\s*words?/i);
    return match ? parseInt(match[1], 10) : 12;
};

</script>