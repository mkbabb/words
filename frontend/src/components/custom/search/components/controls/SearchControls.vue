<template>
    <div
        ref="controlsDropdown"
        class="dropdown-element popover-surface mb-2 flex max-h-[85dvh] origin-top flex-col overflow-hidden bg-background/98 shadow-xl"
        tabindex="0"
        @mousedown.prevent
        @click="$emit('interaction')"
        @keydown.enter="handleEnterKey"
    >
            <!-- Header: Sidebar Toggle + Search Mode Underline Tabs -->
            <div
                class="flex shrink-0 items-center justify-between border-border/30 bg-background/98 px-4 py-3 shadow-sm lg:justify-center"
            >
                <!-- Mobile Sidebar Toggle (far left) -->
                <button
                    class="focus-ring rounded-xl p-2 transition-[background-color,color,transform] duration-200 ease-apple-smooth hover:bg-background hover:shadow-sm lg:hidden"
                    @click="$emit('toggle-sidebar')"
                    title="Toggle Sidebar"
                >
                    <PanelLeft :size="20" class="text-muted-foreground" />
                </button>

                <!-- Search Mode Underline Tabs -->
                <Tabs
                    :model-value="searchMode"
                    class="w-auto"
                    @update:model-value="(value) => handleModeChange(String(value))"
                >
                    <TabsList variant="underline">
                        <TabsTrigger
                            v-for="mode in modes"
                            :key="mode.value"
                            :value="mode.value"
                            class="gap-1.5"
                        >
                            <component :is="modeIcons[mode.value]" class="h-3.5 w-3.5" />
                            {{ mode.label }}
                        </TabsTrigger>
                    </TabsList>
                </Tabs>

                <!-- Spacer for mobile layout balance -->
                <div class="w-10 lg:hidden"></div>
            </div>

            <!-- Mode-Specific Controls (animated switch, scrollable) -->
            <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain">
                    <div>
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
                        <div v-else-if="searchMode === 'wordlist'">
                            <!-- Dashboard button -->
                            <div v-if="wordlistMode.selectedWordlist" class="px-4 pt-2 pb-1">
                                <Button
                                    @click="handleDashboardClick"
                                    variant="glass-subtle"
                                    size="sm"
                                >
                                    <LayoutDashboard :size="14" />
                                    Dashboard
                                </Button>
                            </div>
                            <WordlistControlsPanel
                                v-model:wordlist-filters="wordlistFilters"
                                v-model:wordlist-sort-criteria="wordlistSortCriteria"
                                @navigate="handleNavigate"
                            />
                        </div>
                    </div>
            </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useStores } from '@/stores';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { BookOpen, LayoutDashboard, ListChecks, PanelLeft, Sparkles } from 'lucide-vue-next';

const modeIcons: Record<string, any> = {
    lookup: BookOpen,
    wordlist: ListChecks,
    stage: Sparkles,
};
import { Button, Tabs, TabsList, TabsTrigger } from '@mkbabb/glass-ui';

const modes = [
    { label: 'Lookup', value: 'lookup' },
    { label: 'Wordlist', value: 'wordlist' },
    { label: 'Stage', value: 'stage' },
];
import LookupControlsPanel from './LookupControlsPanel.vue';
import WordlistControlsPanel from './WordlistControlsPanel.vue';
import type { SearchMode } from '../../types';

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
const wordlistMode = useWordlistMode();
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
const handleModeChange = async (newMode: string | string[]) => {
    const typedMode = (Array.isArray(newMode) ? newMode[0] : newMode) as SearchMode;
    if (typedMode !== searchMode.value) {
        await searchBar.setMode(typedMode, searchBar.searchQuery);

        // If switching to wordlist mode with a persisted wordlist, go directly to it
        if (typedMode === 'wordlist' && wordlistMode.selectedWordlist) {
            router.push({ name: 'Wordlist', params: { wordlistId: wordlistMode.selectedWordlist } });
        } else {
            router.push({ name: 'Home' });
        }
    }
};

// Handle navigation from controls panel (close dropdowns)
const handleNavigate = () => {
    searchBar.hideControls();
    searchBar.hideDropdown();
};

// Dashboard button click
const handleDashboardClick = () => {
    wordlistMode.setWordlist(null);
    searchBar.hideControls();
    searchBar.hideDropdown();
    router.push({ name: 'Home' });
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

onMounted(() => {
    document.addEventListener('keydown', keydownHandler, true);
});

onUnmounted(() => {
    document.removeEventListener('keydown', keydownHandler, true);
});

defineExpose({
    element: controlsDropdown,
});
</script>

<style scoped>
/* Mode switch transitions */
.controls-mode-switch-enter-active {
    transition:
        opacity 200ms var(--ease-apple-smooth),
        transform 400ms var(--ease-apple-spring);
}

.controls-mode-switch-leave-active {
    transition:
        opacity 150ms var(--ease-apple-smooth),
        transform 200ms var(--ease-apple-smooth);
}

.controls-mode-switch-enter-from {
    opacity: 0;
    transform: translateY(8px);
}

.controls-mode-switch-enter-to {
    opacity: 1;
    transform: translateY(0);
}

.controls-mode-switch-leave-from {
    opacity: 1;
    transform: translateY(0);
}

.controls-mode-switch-leave-to {
    opacity: 0;
    transform: translateY(-6px);
}
</style>
