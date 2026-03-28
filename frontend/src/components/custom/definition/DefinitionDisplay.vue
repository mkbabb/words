<template>
    <!-- Error State -->
    <div v-if="contentStore.definitionError?.hasError" class="relative">
        <ThemedCard :variant="selectedCardVariant" class="relative">
            <ErrorState
                :title="getErrorTitle(contentStore.definitionError.errorType)"
                :message="contentStore.definitionError.errorMessage"
                :error-type="contentStore.definitionError.errorType"
                :retryable="contentStore.definitionError.canRetry"
                :show-help="
                    contentStore.definitionError.errorType === 'unknown'
                "
                @retry="actions.handleRetryLookup"
                @help="actions.handleShowHelp"
            />
        </ThemedCard>
    </div>

    <!-- Empty State -->
    <div v-else-if="isEmpty && !isStreaming" class="relative">
        <ThemedCard :variant="selectedCardVariant" class="relative">
            <!-- Show mode escape hatch when stuck in non-dictionary mode with no data -->
            <div
                v-if="searchBar.getSubMode('lookup') !== 'dictionary'"
                class="flex items-center justify-center gap-3 border-b border-border/30 px-4 py-3"
            >
                <span class="text-sm text-muted-foreground">
                    No {{ searchBar.getSubMode('lookup') }} data available.
                </span>
                <Button
                    @click="searchBar.setSubMode('lookup', 'dictionary')"
                    variant="outline"
                    size="sm"
                >
                    Switch to Dictionary
                </Button>
            </div>
            <EmptyState
                :title="
                    getEmptyTitle(contentStore.definitionError?.originalWord)
                "
                :message="getEmptyMessage()"
                empty-type="no-definitions"
                :show-suggestions="true"
                @suggest-alternatives="actions.handleSuggestAlternatives"
            >
                <template #actions>
                    <div class="flex items-center gap-3">
                        <Button
                            @click="actions.handleRetryLookup"
                            variant="outline"
                            size="sm"
                        >
                            Try again
                        </Button>
                    </div>
                </template>
            </EmptyState>
        </ThemedCard>
    </div>

    <!-- Stuck Mode Escape: no entry, no error, not empty — mode is stale -->
    <div v-else-if="!entry && !isStreaming && searchBar.getSubMode('lookup') !== 'dictionary'" class="relative">
        <ThemedCard :variant="selectedCardVariant" class="relative">
            <div class="flex flex-col items-center gap-3 p-8 text-center">
                <p class="text-sm text-muted-foreground">
                    No data available for this mode.
                </p>
                <Button
                    @click="searchBar.setSubMode('lookup', 'dictionary')"
                    variant="outline"
                    size="sm"
                >
                    Switch to Dictionary
                </Button>
            </div>
        </ThemedCard>
    </div>

    <!-- Normal Content -->
    <div v-else-if="entry" ref="definitionCardRef" class="paper-article relative">
        <!-- Main Card -->
        <ThemedCard
            :variant="selectedCardVariant"
            :class="[
                'relative transition-[box-shadow] duration-350 ease-apple-default',
                editModeEnabled && 'ring-1 ring-inset ring-muted-foreground/15',
            ]"
        >
            <!-- Image Carousel Display -->
            <ImageCarousel
                :images="allImages"
                :fallbackText="entry.word"
                :editMode="editModeEnabled"
                :synthEntryId="entry.id || undefined"
                @image-error="handleImageError"
                @image-click="handleImageClick"
                @images-updated="actions.handleImagesUpdated"
                @image-deleted="actions.handleImageDeleted"
            />

            <!-- Progressive Header with Smart Skeletons -->
            <WordHeader
                v-if="entry.word && entry.languages?.length"
                :word="entry.word"
                :languages="entry.languages"
                :pronunciation="entry.pronunciation"
                :pronunciationMode="lookupMode.pronunciationMode"
                :providers="usedProviders"
                :active-source="activeSourceTab"
                :show-synthesis="!!entry.model_info"
                :interactive="!sourceSelectionDisabled"
                :source-entries="entry?.source_entries"
                @toggle-pronunciation="lookupMode.togglePronunciation"
                @select-source="activeSourceTab = $event"
            />
            <!-- Header Skeleton -->
            <div v-else-if="isStreaming" class="space-y-4 p-6">
                <div class="flex items-center justify-between">
                    <div class="h-8 w-48 animate-pulse rounded bg-muted" />
                    <div class="h-8 w-24 animate-pulse rounded bg-muted" />
                </div>
                <div class="flex items-center gap-4">
                    <div class="h-6 w-32 animate-pulse rounded bg-muted" />
                    <div class="h-5 w-16 animate-pulse rounded bg-muted" />
                </div>
            </div>

            <!-- Gradient Separator -->
            <hr
                class="mt-1 mb-1 h-[2px] border-0"
                style="background: linear-gradient(to right, transparent 2%, var(--color-border) 15%, var(--color-border) 85%, transparent 98%);"
            />

            <!-- Admin Edit Dock -->
            <DefinitionToolbar
                v-model="selectedCardVariant"
                :isMounted="isMounted"
                :showDropdown="actions.showThemeDropdown.value"
                :editModeEnabled="editModeEnabled"
                :word="entry?.word"
                :currentVersion="entry?.version != null ? String(entry.version) : undefined"
                @toggle-dropdown="
                    actions.showThemeDropdown.value =
                        !actions.showThemeDropdown.value
                "
                @toggle-edit-mode="editModeEnabled = !editModeEnabled"
                @toggle-version-history="actions.handleToggleVersionHistory"
                @resynthesize="actions.handleReSynthesize"
                @add-image="handleAddImage"
            />

            <!-- Provider source tabs (AI Synthesis + raw provider data) -->
            <ProviderViewTabs
                v-model="activeSourceTab"
                :word="entry?.word || ''"
                :available-providers="usedProviders"
                :show-synthesis="!!entry?.model_info"
                :show-version-history="editModeEnabled"
                :edit-mode-enabled="editModeEnabled"
            >
            <!-- Mode Content, Etymology, Phrases, Debug -->
            <DefinitionContentView
                :entry="entry"
                :currentSubMode="searchBar.getSubMode('lookup')"
                :cardVariant="selectedCardVariant"
                :editModeEnabled="editModeEnabled"
                :isStreaming="isStreaming"
                :activeSource="activeSourceTab"
                :thesaurusData="thesaurusData"
                :regeneratingDefinitionIndex="contentStore.regeneratingDefinitionIndex"
                @update:cluster-name="(id: string, name: string) => actions.handleClusterNameUpdate(id, name)"
                @regenerate="actions.handleRegenerateExamples"
                @search-word="actions.handleWordSearch"
                @add-to-wordlist="actions.handleAddToWordlist"
                @retry-thesaurus="actions.handleRetryThesaurus"
                @switch-to-dictionary="searchBar.setSubMode('lookup', 'dictionary')"
            />
            </ProviderViewTabs>
        </ThemedCard>

        <!-- Overlays and Modals -->
        <DefinitionModals
            :word="entry?.word"
            :currentVersion="entry?.version != null ? String(entry.version) : undefined"
            :tmIsOpen="timeMachine.isOpen.value"
            :tmVersions="timeMachine.versions.value"
            :tmSelectedIndex="timeMachine.selectedIndex.value"
            :tmSelectedVersion="timeMachine.selectedVersion.value"
            :tmVersionDetail="timeMachine.versionDetail.value"
            :tmVersionDiff="timeMachine.versionDiff.value"
            :tmDiffFields="timeMachine.diffFields.value"
            :tmTextChanges="timeMachine.textChanges.value"
            :tmHydratedEntry="timeMachine.hydratedEntry.value"
            :tmNavigationDirection="timeMachine.navigationDirection.value"
            :tmLoading="timeMachine.loading.value"
            :tmDetailLoading="timeMachine.detailLoading.value"
            :tmRollingBack="timeMachine.rollingBack.value"
            :tmIsNewest="timeMachine.isNewest.value"
            :tmIsOldest="timeMachine.isOldest.value"
            :tmExpandedView="timeMachine.expandedView.value"
            :ilSelectedWord="inlineLookup.selectedWord.value"
            :ilIsPillVisible="inlineLookup.isPillVisible.value"
            :ilIsPopoverVisible="inlineLookup.isPopoverVisible.value"
            :ilPosition="inlineLookup.position.value"
            v-model:showWordlistModal="actions.showWordlistModal.value"
            :wordToAdd="actions.wordToAdd.value"
            @time-machine-close="handleTimeMachineClose"
            @time-machine-select-version="timeMachine.selectVersion"
            @time-machine-navigate-next="timeMachine.navigateNext"
            @time-machine-navigate-prev="timeMachine.navigatePrev"
            @time-machine-rollback="handleTimeMachineRollback"
            @time-machine-toggle-expanded="timeMachine.toggleExpanded"
            @inline-show-popover="inlineLookup.showPopover"
            @inline-dismiss="inlineLookup.dismiss"
            @inline-lookup="handleInlineLookup"
            @inline-add-to-wordlist="handleInlineAddToWordlist"
            @word-added-to-list="actions.handleWordAddedToList"
        />
    </div>
</template>

<script setup lang="ts">
import { computed, provide, ref, watch } from 'vue';
import { useContentStore } from '@/stores';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';
import { Button } from '@mkbabb/glass-ui';
import { PAPER_CONTEXT, useKatex, createRenderTitle } from '@mkbabb/latex-paper/vue';
import {
    WordHeader,
    ImageCarousel,
    ErrorState,
    EmptyState,
} from './components';
import { ThemedCard } from '@/components/custom/card';
import ProviderViewTabs from './components/ProviderViewTabs.vue';
import DefinitionToolbar from './components/DefinitionToolbar.vue';
import DefinitionContentView from './components/content/DefinitionContentView.vue';
import DefinitionModals from './components/DefinitionModals.vue';
import {
    useProviders,
    useImageManagement,
    useDefinitionActions,
    useTimeMachine,
} from './composables';
import { useEntryState } from './composables/useEntryState';
import { useSourceTabManagement } from './composables/useSourceTabManagement';
import {
    getErrorTitle,
    getEmptyTitle,
    getEmptyMessage,
} from './utils/stateMessages';
import { useRouter } from 'vue-router';
import { useInlineWordLookup } from '@/composables/useInlineWordLookup';

// Stores
const contentStore = useContentStore();
const lookupMode = useLookupMode();
const searchBar = useSearchBarStore();

// Set up shared KaTeX rendering context for all definition content
const { renderInline, renderDisplay } = useKatex({
    '\\mathscr': '\\mathcal',
    '\\ornate': '\\mathfrak',
});

provide(PAPER_CONTEXT, {
    sections: [],
    labelMap: {},
    renderInline,
    renderDisplay,
    renderTitle: createRenderTitle(renderInline),
    assetBase: '',
    scrollToId: () => {},
});

// Orchestrator for auto-fetching thesaurus data
const orchestrator = useSearchOrchestrator({
    query: computed(() => searchBar.searchQuery),
});

// Auto-fetch thesaurus when switching to thesaurus submode
watch(() => searchBar.getSubMode('lookup'), async (newSubMode) => {
    if (
        newSubMode === 'thesaurus' &&
        contentStore.currentEntry &&
        !contentStore.currentThesaurus
    ) {
        const word = contentStore.currentEntry.word;
        const data = await orchestrator.getThesaurusData(word);
        if (data) {
            contentStore.setCurrentThesaurus(data);
        }
    }
});

// Reactive state
const isMounted = ref(true);
const editModeEnabled = ref(false);

// UI State computed properties
const selectedCardVariant = computed({
    get: () => lookupMode.selectedCardVariant,
    set: (value) => lookupMode.setCardVariant(value),
});

// Entry state (merged streaming + complete data, isEmpty, isStreaming, thesaurusData)
// We need activeSourceTab for thesaurusData, but sourceTab depends on usedProviders which depends on entry.
// Break the cycle: create a temporary ref for activeSourceTab, then wire up once both are ready.
const tempActiveSourceTab = ref('synthesis');
const entryState = useEntryState(tempActiveSourceTab);
const { entry, isStreaming, isEmpty, thesaurusData } = entryState;

// Providers derived from entry
const { usedProviders } = useProviders(entry);

// Source tab management
const sourceTab = useSourceTabManagement(entry, usedProviders);
const { activeSourceTab, sourceSelectionDisabled } = sourceTab;

// Sync the temp ref so thesaurusData stays reactive
watch(activeSourceTab, (v) => { tempActiveSourceTab.value = v; }, { immediate: true });

const { allImages, handleImageClick, handleImageError } =
    useImageManagement(entry);
const actions = useDefinitionActions({ entry, editModeEnabled });
const timeMachine = useTimeMachine(computed(() => entry.value?.word));

// Inline word lookup
const definitionCardRef = ref<HTMLElement | null>(null);
const inlineLookup = useInlineWordLookup(definitionCardRef);

// Router captured in setup context
const router = useRouter();

function handleInlineLookup(word: string) {
    inlineLookup.dismiss();
    router.push({ name: 'Definition', params: { word } });
}

function handleInlineAddToWordlist(word: string) {
    inlineLookup.dismiss();
    actions.handleAddToWordlist(word);
}

// Image upload handler
const imageFileInput = ref<HTMLInputElement | null>(null);
function handleAddImage() {
    if (!imageFileInput.value) {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.style.display = 'none';
        input.addEventListener('change', async () => {
            const file = input.files?.[0];
            if (!file || !entry.value?.id) return;
            try {
                const [{ mediaApi: imgApi }, { entriesApi }] = await Promise.all([
                    import('@/api/media'),
                    import('@/api/entries'),
                ]);
                const uploaded = await imgApi.uploadImage(file, {
                    alt_text: file.name.replace(/\.[^/.]+$/, ''),
                });
                await entriesApi.addImagesToEntry(entry.value.id, [uploaded.id]);
                actions.handleImagesUpdated([uploaded]);
            } catch {
                // Silently degrade
            }
            input.value = '';
        });
        document.body.appendChild(input);
        imageFileInput.value = input;
    }
    imageFileInput.value.click();
}

// Wire up version history toggle to Time Machine
watch(() => actions.showVersionHistory.value, (show) => {
    if (show) {
        timeMachine.open();
        actions.showVersionHistory.value = false;
    }
});

// Time Machine handlers
const handleTimeMachineClose = () => {
    timeMachine.close();
};

const handleTimeMachineRollback = async () => {
    await timeMachine.handleRollback();
    if (entry.value?.word) {
        const orchestrator2 = useSearchOrchestrator({
            query: computed(() => entry.value?.word || ''),
        });
        try {
            await orchestrator2.getDefinition(entry.value.word);
        } catch {
            // Silently fail
        }
    }
};
</script>

<style scoped>
/* Ensure proper stacking context */
.sticky {
    will-change: transform;
}
</style>
