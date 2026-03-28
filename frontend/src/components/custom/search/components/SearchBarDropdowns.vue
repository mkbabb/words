<template>
    <div
        class="absolute top-full left-0 right-0 z-dock pt-1"
        :class="{ 'pointer-events-none': !searchBar.showSearchControls && !searchBar.showDropdown }"
    >
        <!-- Controls Dropdown — grid-based height transition wrapper -->
        <div
            :class="[
                'controls-dropdown-wrapper',
                searchBar.showSearchControls
                    ? 'controls-dropdown-open pointer-events-auto'
                    : 'controls-dropdown-closed',
            ]"
        >
            <SearchControls
                class="min-h-0 overflow-hidden"
                :show="true"
                v-model:selected-sources="selectedSources"
                v-model:selected-languages="selectedLanguages"
                v-model:no-a-i="noAI"
                v-model:wordlist-filters="wordlistFilters"
                :wordlist-sort-criteria="wordlistSortCriteria"
                @update:wordlist-sort-criteria="(value: any) => (wordlistSortCriteria = value)"
                :ai-suggestions="searchBar.aiSuggestions as string[]"
                :is-development="isDevelopment"
                :show-refresh-button="showRefreshButton"
                :force-refresh-mode="forceRefreshMode"
                @word-select="$emit('word-select', $event)"
                @clear-storage="$emit('clear-storage')"
                @interaction="$emit('interaction')"
                @toggle-sidebar="$emit('toggle-sidebar')"
                @toggle-refresh="$emit('toggle-refresh')"
                @execute-search="$emit('execute-search')"
            />
        </div>

        <!-- Search Results Container -->
        <div :class="{ 'pointer-events-auto': searchBar.showDropdown }">
            <SearchResults
                ref="searchResultsComponent"
                :show="searchBar.showDropdown"
                :results="results"
                :loading="isSearching"
                v-model:selected-index="selectedIndex"
                :query="query"
                :ai-mode="searchBar.isAIQuery"
                :recent-searches="recentSearches"
                @select-result="$emit('select-result', $event)"
                @interaction="$emit('interaction')"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useSearchBarStore } from '@/stores/search/search-bar';
import SearchControls from './controls/SearchControls.vue';
import SearchResults from './results/SearchResults.vue';

interface Props {
    isDevelopment: boolean;
    showRefreshButton: boolean;
    forceRefreshMode: boolean;
    results: any[];
    isSearching: boolean;
    query: string;
    recentSearches: any[];
}

defineProps<Props>();

const selectedSources = defineModel<string[]>('selectedSources', { required: true });
const selectedLanguages = defineModel<string[]>('selectedLanguages', { required: true });
const noAI = defineModel<boolean>('noAI', { required: true });
const wordlistFilters = defineModel<any>('wordlistFilters', { required: true });
const wordlistSortCriteria = defineModel<any>('wordlistSortCriteria', { required: true });
const selectedIndex = defineModel<number>('selectedIndex', { required: true });

defineEmits<{
    'word-select': [word: string];
    'clear-storage': [];
    interaction: [];
    'toggle-sidebar': [];
    'toggle-refresh': [];
    'execute-search': [];
    'select-result': [result: any];
}>();

const searchBar = useSearchBarStore();

const searchResultsComponent = ref<any>();

defineExpose({
    searchResultsComponent,
});
</script>

<style scoped>
/*
 * Controls dropdown: grid-based height animation.
 * Uses grid-template-rows 0fr/1fr for smooth collapse without max-height.
 */
.controls-dropdown-wrapper {
    display: grid;
    will-change: grid-template-rows, opacity;
}

.controls-dropdown-open {
    grid-template-rows: 1fr;
    opacity: 1;
    margin-bottom: 0.25rem;
    transition:
        grid-template-rows 250ms cubic-bezier(0.4, 0, 0.2, 1),
        opacity 150ms cubic-bezier(0, 0, 0.2, 1),
        margin-bottom 250ms cubic-bezier(0.4, 0, 0.2, 1);
}

.controls-dropdown-closed {
    grid-template-rows: 0fr;
    opacity: 0;
    margin-bottom: 0;
    transition:
        grid-template-rows 180ms cubic-bezier(0.4, 0, 1, 1),
        opacity 120ms cubic-bezier(0.4, 0, 1, 1) 30ms,
        margin-bottom 180ms cubic-bezier(0.4, 0, 1, 1);
}
</style>
