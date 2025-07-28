<template>
    <div class="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div class="min-h-0 flex-1 overflow-y-auto p-4 overscroll-contain">
            <!-- Show different views based on search mode -->
            <template v-if="!collapsed">
                <Transition
                    mode="out-in"
                    enter-active-class="transition-all duration-300 ease-out"
                    enter-from-class="opacity-0 translate-x-4"
                    enter-to-class="opacity-100 translate-x-0"
                    leave-active-class="transition-all duration-200 ease-in"
                    leave-from-class="opacity-100 translate-x-0"
                    leave-to-class="opacity-0 -translate-x-4"
                >
                    <component 
                        :is="currentView" 
                        :key="store.searchMode"
                    />
                </Transition>
            </template>
            
            <!-- Collapsed state -->
            <div v-else class="flex flex-col items-center gap-2">
                <!-- Recent words for lookup mode -->
                <template v-if="store.searchMode === 'lookup'">
                    <HoverCard v-for="item in combinedRecentItems" :key="item.id">
                        <HoverCardTrigger as-child>
                            <button 
                                @click="item.type === 'lookup' ? handleCollapsedWordClick(item.word!) : handleCollapsedAIClick(item.query!)"
                                class="flex h-10 w-10 items-center justify-center rounded-lg border border-border/50 bg-muted/30 hover:bg-muted/50 hover:border-border transition-all duration-200 text-sm font-medium"
                                :class="{ 'bg-yellow-500/10 border-yellow-500/20 hover:bg-yellow-500/20': item.type === 'ai' }"
                            >
                                <template v-if="item.type === 'lookup'">
                                    {{ item.word!.substring(0, 2).toUpperCase() }}
                                </template>
                                <template v-else>
                                    AI
                                </template>
                            </button>
                        </HoverCardTrigger>
                        <HoverCardContent side="right" :sideOffset="5" class="w-64">
                            <div class="space-y-2">
                                <template v-if="item.type === 'lookup'">
                                    <h4 class="font-semibold">{{ item.word }}</h4>
                                    <p v-if="getFirstDefinition(item.entry!)" class="text-sm text-muted-foreground">
                                        {{ getFirstDefinition(item.entry!) }}
                                    </p>
                                </template>
                                <template v-else>
                                    <h4 class="font-semibold text-yellow-600 dark:text-yellow-400">AI Query</h4>
                                    <p class="text-sm text-muted-foreground">{{ item.query }}</p>
                                </template>
                                <p class="text-xs text-muted-foreground/70">
                                    {{ formatTimestamp(item.timestamp) }}
                                </p>
                            </div>
                        </HoverCardContent>
                    </HoverCard>
                </template>
                
                <!-- Placeholder for wordlist/stage modes -->
                <template v-else>
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger as-child>
                                <button 
                                    @click="store.setSidebarCollapsed(false)"
                                    class="flex h-10 w-10 items-center justify-center rounded-lg hover:bg-muted/50 transition-colors"
                                >
                                    <FileText :size="18" class="text-muted-foreground" />
                                </button>
                            </TooltipTrigger>
                            <TooltipContent side="right">
                                <p>Word Lists</p>
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                </template>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useAppStore } from '@/stores';
import { FileText } from 'lucide-vue-next';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import SidebarLookupView from './SidebarLookupView.vue';
import SidebarWordListView from './SidebarWordListView.vue';
import type { SynthesizedDictionaryEntry } from '@/types';

interface Props {
    collapsed: boolean;
    mobile?: boolean;
}

defineProps<Props>();

const store = useAppStore();
const { recentLookups, aiQueryHistory } = storeToRefs(store);

// Combine lookups and AI queries for collapsed view
interface CombinedItem {
    id: string;
    type: 'lookup' | 'ai';
    word?: string;
    query?: string;
    timestamp: Date;
    entry?: SynthesizedDictionaryEntry;
}

const combinedRecentItems = computed<CombinedItem[]>(() => {
    const lookups: CombinedItem[] = recentLookups.value.map(lookup => ({
        id: lookup.id,
        type: 'lookup' as const,
        word: lookup.word,
        timestamp: new Date(lookup.timestamp),
        entry: lookup.entry
    }));
    
    const aiQueries: CombinedItem[] = aiQueryHistory.value.map((item, index) => ({
        id: `ai-${index}-${item.timestamp}`,
        type: 'ai' as const,
        query: item.query,
        timestamp: new Date(item.timestamp)
    }));
    
    // Combine and sort by timestamp (newest first)
    return [...lookups, ...aiQueries]
        .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
        .slice(0, 8);
});

// Determine which view to show based on search mode
const currentView = computed(() => {
    // Show word list view for 'wordlist' and 'stage' modes
    if (store.searchMode === 'wordlist' || store.searchMode === 'stage') {
        return SidebarWordListView;
    }
    // Default to lookup view for 'lookup' mode
    return SidebarLookupView;
});

const handleCollapsedWordClick = async (word: string) => {
    store.searchQuery = word;
    await store.searchWord(word);
};

const handleCollapsedAIClick = async (query: string) => {
    // Set query and enable AI mode
    store.searchQuery = query;
    store.sessionState.isAIQuery = true;
    store.sessionState.aiQueryText = query;
    store.mode = 'suggestions';
    
    // Trigger AI suggestions search
    try {
        // Extract word count from the query (default to 12)
        const wordCount = extractWordCount(query);
        const results = await store.getAISuggestions(query, wordCount);
        
        if (results && results.suggestions.length > 0) {
            store.wordSuggestions = results;
            store.hasSearched = true;
        }
    } catch (error) {
        console.error('Error getting AI suggestions:', error);
    }
};

// Helper function to extract word count from query
const extractWordCount = (query: string): number => {
    const match = query.match(/(\d+)\s*words?/i);
    return match ? parseInt(match[1], 10) : 12;
};

const getFirstDefinition = (entry: SynthesizedDictionaryEntry): string => {
    const firstDef = entry.definitions?.[0];
    if (!firstDef) return '';
    
    const text = firstDef.definition || firstDef.text || '';
    return text.length > 60 ? text.substring(0, 60) + '...' : text;
};

const formatTimestamp = (timestamp: Date): string => {
    const now = new Date();
    const date = new Date(timestamp);
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString();
};
</script>