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
import { computed, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useRouter } from 'vue-router';
import { useStores } from '@/stores';
import { Accordion } from '@/components/ui/accordion';
import { Book, Search, Wand2 } from 'lucide-vue-next';
import { capitalizeFirst } from '@/utils';
import SidebarSection from './SidebarSection.vue';
import GoldenSidebarSection from './GoldenSidebarSection.vue';
import SidebarRecentItem from './SidebarRecentItem.vue';
import VocabularySuggestionItem from './VocabularySuggestionItem.vue';
import type { SynthesizedDictionaryEntry } from '@/types';

const { history, orchestrator, ui, searchBar } = useStores();
const router = useRouter();
const { recentLookups, vocabularySuggestions, recentSearches, aiQueryHistory } = storeToRefs(history);

// Computed property to format AI query history for display
const recentAISuggestions = computed(() => 
    aiQueryHistory.value.map(item => ({
        query: item.query,
        timestamp: new Date(item.timestamp)
    }))
);

// Accordion state management - default to collapsed (empty array)
const accordionValue = computed({
    get: () => ui.sidebarAccordionState.lookup || [],
    set: (value) => {
        ui.setSidebarAccordionState('lookup', value as string[]);
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
    
    // Navigate to appropriate route based on mode
    const routeName = ui.mode === 'thesaurus' ? 'Thesaurus' : 'Definition';
    router.push({ name: routeName, params: { word: lookup.word } });
    
    await orchestrator.searchWord(lookup.word);
    // Close mobile sidebar if open
    if (ui.sidebarOpen) {
        ui.toggleSidebar();
    }
};

const handleSuggestionClick = async (suggestion: { word: string }) => {
    searchBar.setQuery(suggestion.word);
    
    // Switch to dictionary mode for word lookup (vocab suggestions are word lookups)
    ui.setMode('dictionary');
    
    // Navigate to Definition route
    router.push({ name: 'Definition', params: { word: suggestion.word } });
    
    await orchestrator.searchWord(suggestion.word);
    // Close mobile sidebar if open
    if (ui.sidebarOpen) {
        ui.toggleSidebar();
    }
};


const handleSearchClick = async (search: { query: string }) => {
    // Navigate to appropriate route based on mode
    const routeName = ui.mode === 'thesaurus' ? 'Thesaurus' : 'Definition';
    router.push({ name: routeName, params: { word: search.query } });
    
    // Use the centralized searchWord action which handles dropdown hiding
    await orchestrator.searchWord(search.query);
    
    // Close mobile sidebar if open
    if (ui.sidebarOpen) {
        ui.toggleSidebar();
    }
};

const handleAISuggestionClick = async (suggestion: { query: string }) => {
    // Set mode to suggestions
    ui.setMode('suggestions');
    
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
        console.error('Error getting AI suggestions:', error);
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
    console.log('🔍 SidebarLookupView mounted - checking history and suggestions');
    console.log('Recent lookups count:', history.recentLookups.length);
    console.log('Current vocab suggestions count:', history.vocabularySuggestions.length);
    console.log('Recent lookup words:', history.recentLookupWords.slice(0, 5));
    
    // If no lookup history exists, add some test data for vocabulary suggestions
    if (history.recentLookups.length === 0) {
        console.log('📝 No lookup history found. Adding test data for vocabulary suggestions...');
        
        // Add some sample lookup history to test vocabulary suggestions
        const sampleWords = ['eloquent', 'serendipity', 'ephemeral', 'ubiquitous', 'perspicacious'];
        
        for (const word of sampleWords) {
            // Create a minimal entry for testing
            const mockEntry = {
                id: `test-${word}`,
                word,
                word_id: `test-${word}`,
                definitions: [{
                    id: `def-${word}`,
                    word_id: `test-${word}`,
                    text: `Sample definition for ${word}`,
                    part_of_speech: 'adjective',
                    examples: [],
                    images: [],
                    providers_data: []
                }],
                synonyms: [],
                antonyms: [],
                facts: [],
                images: [],
                pronunciations: [],
                etymology: null,
                version: 1
            };
            
            history.addToLookupHistory(word, mockEntry as any);
        }
        
        console.log('📝 Added', sampleWords.length, 'test lookups. New count:', history.recentLookups.length);
    }
    
    // Always try to refresh vocabulary suggestions
    try {
        console.log('🔄 Attempting to refresh vocabulary suggestions...');
        await history.refreshVocabularySuggestions(true); // Force refresh
        console.log('✅ Vocabulary suggestions refreshed. Count:', history.vocabularySuggestions.length);
        
        if (history.vocabularySuggestions.length === 0) {
            console.warn('⚠️ No vocabulary suggestions returned from API');
        }
    } catch (error) {
        console.error('❌ Failed to refresh vocabulary suggestions:', error);
        
        // If API fails, create some fallback suggestions based on recent lookups
        console.log('🔄 Creating fallback vocabulary suggestions...');
        const fallbackSuggestions = history.recentLookupWords.slice(0, 3).map(word => ({
            word: `related-${word}`,
            reasoning: `A word related to ${word}`,
            difficulty_level: 3,
            semantic_category: 'general'
        }));
        
        // Manually set some test suggestions for development
        if (fallbackSuggestions.length === 0) {
            const devSuggestions = [
                { word: 'mellifluous', reasoning: 'A beautiful word meaning sweet-sounding', difficulty_level: 4, semantic_category: 'descriptive' },
                { word: 'ineffable', reasoning: 'Something too great to be expressed in words', difficulty_level: 5, semantic_category: 'abstract' },
                { word: 'susurrus', reasoning: 'A soft murmuring or rustling sound', difficulty_level: 4, semantic_category: 'sensory' }
            ];
            
            console.log('📝 Using development vocabulary suggestions:', devSuggestions);
            // For now, just log them - in a real scenario we'd need to set them in the store
        }
    }
});

</script>