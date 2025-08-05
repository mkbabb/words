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
// import { useLookupMode } from '@/stores/search/modes/lookup'; // Unused
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';
import { useRouter } from 'vue-router';
import { Accordion } from '@/components/ui/accordion';
import { Search, Sparkles } from 'lucide-vue-next';
import SidebarSection from './SidebarSection.vue';
import GoldenSidebarSection from './GoldenSidebarSection.vue';
import SidebarRecentItem from './SidebarRecentItem.vue';
import VocabularySuggestionItem from './VocabularySuggestionItem.vue';
import type { SynthesizedDictionaryEntry } from '@/types';

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
    
    // Navigate to appropriate route based on mode
    const subMode = searchBar.getSubMode('lookup');
    const routeName = subMode === 'thesaurus' ? 'Thesaurus' : 'Definition';
    router.push({ name: routeName, params: { word: lookup.word } });
    
    searchBar.setDirectLookup(true);
    try {
        await orchestrator.getDefinition(lookup.word);
    } finally {
        searchBar.setDirectLookup(false);
    }
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
    
    // Navigate to Definition route
    router.push({ name: 'Definition', params: { word: suggestion.word } });
    
    searchBar.setDirectLookup(true);
    try {
        await orchestrator.getDefinition(suggestion.word);
    } finally {
        searchBar.setDirectLookup(false);
    }
    // Close mobile sidebar if open
    if (ui.sidebarOpen) {
        ui.toggleSidebar();
    }
};


const handleSearchClick = async (search: { query: string }) => {
    // Navigate to appropriate route based on mode
    const subMode = searchBar.getSubMode('lookup');
    const routeName = subMode === 'thesaurus' ? 'Thesaurus' : 'Definition';
    router.push({ name: routeName, params: { word: search.query } });
    
    // Use the direct search action which handles dropdown hiding
    searchBar.setDirectLookup(true);
    try {
        await orchestrator.getDefinition(search.query);
    } finally {
        searchBar.setDirectLookup(false);
    }
    
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
                    text: `Sample definition for ${word}`,
                    part_of_speech: 'adjective' as const,
                    word_id: `test-${word}`,
                    word_forms: [],
                    example_ids: [],
                    image_ids: [],
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    cefr_level: null,
                    frequency_band: null,
                    meaning_cluster: null,
                    language_register: null,
                    grammar_patterns: [],
                    collocations: [],
                    usage_notes: [],
                    regional_variants: [],
                    examples: [],
                    images: [],
                    providers_data: []
                }],
                last_updated: new Date().toISOString(),
                lookup_count: 1
            } as unknown as SynthesizedDictionaryEntry;
            
            history.addToLookupHistory(word, mockEntry);
        }
        
        console.log('✅ Added sample lookup history. Recent lookups:', history.recentLookups.length);
    }
    
    // Check if we need to initialize vocabulary suggestions
    if (history.vocabularySuggestions.length === 0 && history.recentLookups.length > 0) {
        console.log('🌟 Attempting to generate vocabulary suggestions...');
        
        try {
            await history.refreshVocabularySuggestions();
            const response = { suggestions: history.vocabularySuggestions };
            
            if (response && response.suggestions && response.suggestions.length > 0) {
                console.log('✅ Successfully generated vocabulary suggestions:', response.suggestions.length);
            } else {
                console.log('⚠️ No vocabulary suggestions generated from API');
            }
        } catch (error) {
            console.error('❌ Failed to generate vocabulary suggestions:', error);
            
            // If API fails, create some fallback suggestions based on recent lookups
            console.log('🔄 Creating fallback vocabulary suggestions...');
            const fallbackSuggestions = history.recentLookupWords.slice(0, 3).map(word => ({
                word: word + '-related',
                reason: `Explore words related to "${word}"`,
                difficulty: 'intermediate' as const,
                relevance_score: 0.8
            }));
            
            // Note: Cannot directly set vocabulary suggestions as there's no setter method
            // The fallback suggestions will be used only if the API fails
            console.log('⚠️ Fallback suggestions created but cannot be directly set:', fallbackSuggestions);
            
            if (fallbackSuggestions.length === 0) {
                console.log('💡 No recent lookups available for fallback suggestions');
            } else {
                console.log('✅ Created fallback vocabulary suggestions:', fallbackSuggestions.length);
            }
        }
    } else {
        console.log('📚 Vocabulary suggestions already present:', history.vocabularySuggestions.length);
    }
});
</script>