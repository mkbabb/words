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
            <div v-else class="space-y-4">
                <!-- Recent words for lookup mode -->
                <template v-if="store.searchMode === 'lookup'">
                    <TooltipProvider v-for="word in recentLookupWords.slice(0, 8)" :key="word">
                        <Tooltip>
                            <TooltipTrigger as-child>
                                <button 
                                    @click="handleCollapsedWordClick(word)"
                                    class="flex h-10 w-10 items-center justify-center rounded-lg hover:bg-muted/50 transition-colors text-sm font-medium"
                                >
                                    {{ word.substring(0, 2).toUpperCase() }}
                                </button>
                            </TooltipTrigger>
                            <TooltipContent side="right">
                                <p>{{ word }}</p>
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
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
import SidebarLookupView from './SidebarLookupView.vue';
import SidebarWordListView from './SidebarWordListView.vue';

interface Props {
    collapsed: boolean;
    mobile?: boolean;
}

defineProps<Props>();

const store = useAppStore();
const { recentLookupWords } = storeToRefs(store);

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
    store.setSidebarCollapsed(false);
};
</script>