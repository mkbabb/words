<template>
    <Transition
        enter-active-class="transition-all duration-350 ease-apple-elastic"
        leave-active-class="transition-all duration-200 ease-apple-bounce-in"
        enter-from-class="opacity-0 scale-90 -translate-y-6 -rotate-1"
        enter-to-class="opacity-100 scale-100 translate-y-0 rotate-0"
        leave-from-class="opacity-100 scale-100 translate-y-0 rotate-0"
        leave-to-class="opacity-0 scale-90 -translate-y-6 -rotate-1"
    >
        <div
            v-if="show"
            ref="controlsDropdown"
            class="dropdown-element cartoon-shadow-sm mb-2 origin-top overflow-hidden rounded-2xl border-2 border-border bg-background/20 backdrop-blur-3xl"
            tabindex="0"
            @mousedown.prevent
            @click="$emit('interaction')"
            @keydown.enter="handleEnterKey"
        >
            <!-- Header: Sidebar Toggle + Search Mode Toggle -->
            <div
                class="flex items-center justify-between border-border/50 px-4 py-3 lg:justify-center"
            >
                <!-- Mobile Sidebar Toggle (far left) -->
                <button
                    class="rounded-lg p-2 transition-colors duration-200 hover:bg-muted/50 lg:hidden"
                    @click="$emit('toggle-sidebar')"
                    title="Toggle Sidebar"
                >
                    <PanelLeft :size="20" class="text-muted-foreground" />
                </button>

                <!-- Search Mode Toggle (center on mobile, full width on desktop) -->
                <BouncyToggle
                    :model-value="searchMode"
                    @update:model-value="handleModeChange"
                    :options="[
                        { label: 'Lookup', value: 'lookup' },
                        { label: 'Wordlist', value: 'wordlist' },
                        { label: 'Stage', value: 'stage' },
                    ]"
                    class="text-base font-bold"
                />

                <!-- Spacer for mobile layout balance -->
                <div class="w-10 lg:hidden"></div>
            </div>

            <!-- Lookup Mode Controls -->
            <LookupControlsPanel
                v-if="searchMode === 'lookup'"
                v-model:selected-sources="selectedSources"
                v-model:selected-languages="selectedLanguages"
                v-model:no-a-i="noAI"
                :ai-suggestions="aiSuggestions"
                :is-development="isDevelopment"
                :show-refresh-button="showRefreshButton"
                :force-refresh-mode="forceRefreshMode"
                @word-select="$emit('word-select', $event)"
                @clear-storage="emit('clear-storage')"
                @toggle-sidebar="emit('toggle-sidebar')"
                @toggle-refresh="emit('toggle-refresh')"
            />

            <!-- Wordlist Mode Controls -->
            <WordlistControlsPanel
                v-if="searchMode === 'wordlist'"
                v-model:wordlist-filters="wordlistFilters"
                v-model:wordlist-sort-criteria="wordlistSortCriteria"
            />
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { useStores } from '@/stores';
import { BouncyToggle } from '@/components/custom/animation';
import { PanelLeft } from 'lucide-vue-next';
import LookupControlsPanel from './LookupControlsPanel.vue';
import WordlistControlsPanel from './WordlistControlsPanel.vue';
import type { SearchMode } from '../types';

interface SearchControlsProps {
    show: boolean;
    aiSuggestions: string[];
    isDevelopment: boolean;
    showRefreshButton?: boolean;
    forceRefreshMode?: boolean;
}

const props = defineProps<SearchControlsProps>();

const router = useRouter();
const { searchBar } = useStores();
const searchMode = computed(() => searchBar.searchMode);

const selectedSources = defineModel<string[]>('selectedSources', {
    required: true,
});
const selectedLanguages = defineModel<string[]>('selectedLanguages', {
    required: true,
});
const noAI = defineModel<boolean>('noAI', { required: true });
const wordlistFilters = defineModel<{
    showBronze: boolean;
    showSilver: boolean;
    showGold: boolean;
    showHotOnly: boolean;
    showDueOnly: boolean;
}>('wordlistFilters', {
    required: false,
    default: () => ({
        showBronze: true,
        showSilver: true,
        showGold: true,
        showHotOnly: false,
        showDueOnly: false,
    }),
});

const wordlistSortCriteria = defineModel<any[]>('wordlistSortCriteria', {
    required: false,
    default: () => [],
});

const emit = defineEmits<{
    'word-select': [word: string];
    'clear-storage': [];
    interaction: [];
    'toggle-sidebar': [];
    'toggle-refresh': [];
    'execute-search': [];
}>();

const controlsDropdown = ref<HTMLDivElement>();

// Emit is used in template
void emit;

// Handle enter key press
const handleEnterKey = (event: KeyboardEvent) => {
    event.preventDefault();
    event.stopPropagation();
    emit('execute-search');
};

// Handle mode change from BouncyToggle
const handleModeChange = async (newMode: string | SearchMode) => {
    const typedMode = newMode as SearchMode;
    if (typedMode !== searchMode.value) {
        const currentQuery = searchBar.searchQuery;
        const savedQuery = await searchBar.setMode(typedMode, currentQuery);

        if (savedQuery) {
            searchBar.setQuery(savedQuery);
        } else if (typedMode !== 'lookup') {
            searchBar.setQuery('');
        }

        router.push({ name: 'Home' });
    }
};

// Global enter key handler when controls are visible
const handleGlobalEnter = (event: KeyboardEvent) => {
    if (!props.show) return;

    event.preventDefault();
    event.stopPropagation();
    emit('execute-search');
};

const keydownHandler = (e: KeyboardEvent) => {
    if (e.key === 'Enter') {
        handleGlobalEnter(e);
    }
};

const setupEnterKeyHandling = async () => {
    await nextTick();
};

watch(
    () => props.show,
    async (newVal) => {
        if (newVal) {
            await setupEnterKeyHandling();
        }
    }
);

onMounted(() => {
    document.addEventListener('keydown', keydownHandler, true);

    if (props.show) {
        setupEnterKeyHandling();
    }
});

onUnmounted(() => {
    document.removeEventListener('keydown', keydownHandler, true);
});

defineExpose({
    element: controlsDropdown,
});
</script>
