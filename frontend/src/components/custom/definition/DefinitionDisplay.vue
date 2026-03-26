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
    <div v-else-if="entry" ref="definitionCardRef" class="relative">
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
            :timeMachineState="timeMachineState"
            :inlineLookupState="inlineLookupState"
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
import { computed, ref, watch } from 'vue';
import { useContentStore } from '@/stores';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';
import { Button } from '@/components/ui/button';
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
import {
    getErrorTitle,
    getEmptyTitle,
    getEmptyMessage,
} from './utils/stateMessages';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';
import { useInlineWordLookup } from '@/composables/useInlineWordLookup';

// Stores
const contentStore = useContentStore();
const lookupMode = useLookupMode();
const searchBar = useSearchBarStore();
const authStore = useAuthStore();

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

// Backed by content store so sidebar can read it
const activeSourceTab = computed({
    get: () => contentStore.activeSourceTab,
    set: (v: string) => contentStore.setActiveSourceTab(v),
});

// In dev mode, treat user as premium (matching backend's admin passthrough)
const effectivelyPremium = computed(() =>
    authStore.isPremium || import.meta.env.DEV
);

// Smart computed properties - merge streaming and complete data
const entry = computed(() => {
    if (contentStore.definitionError?.hasError) {
        return null;
    }

    if (contentStore.isStreamingData && contentStore.partialEntry) {
        return {
            word:
                contentStore.partialEntry.word ||
                contentStore.currentEntry?.word,
            id: contentStore.partialEntry.id || contentStore.currentEntry?.id,
            last_updated:
                contentStore.partialEntry.last_updated ||
                contentStore.currentEntry?.last_updated,
            model_info:
                contentStore.partialEntry.model_info ||
                contentStore.currentEntry?.model_info,
            pronunciation:
                contentStore.partialEntry.pronunciation ||
                contentStore.currentEntry?.pronunciation,
            languages:
                contentStore.partialEntry.languages ||
                contentStore.currentEntry?.languages ||
                [],
            etymology:
                contentStore.partialEntry.etymology ||
                contentStore.currentEntry?.etymology,
            images: [
                ...(contentStore.partialEntry.images || []),
                ...(contentStore.currentEntry?.images || []),
            ],
            definitions:
                contentStore.partialEntry.definitions ||
                contentStore.currentEntry?.definitions ||
                [],
            source_entries:
                contentStore.currentEntry?.source_entries ||
                [],
            _isStreaming: true,
            _streamingProgress: 0,
        } as any;
    }

    return contentStore.currentEntry
        ? ({
              ...contentStore.currentEntry,
              _isStreaming: false,
          } as any)
        : null;
});

// Streaming state indicators
const isStreaming = computed(() => contentStore.isStreamingData);

// UI State computed properties
const selectedCardVariant = computed({
    get: () => lookupMode.selectedCardVariant,
    set: (value) => lookupMode.setCardVariant(value),
});

// Thesaurus data (with provider synonym extraction)
const thesaurusData = computed(() => {
    const currentSource = activeSourceTab.value;

    if (currentSource && currentSource !== 'synthesis' && entry.value) {
        const providerSynonyms = extractProviderSynonyms(entry.value, currentSource);
        if (providerSynonyms.length > 0) {
            return {
                word: entry.value.word,
                synonyms: providerSynonyms,
                confidence: 0.7,
            };
        }
    }

    const data = contentStore.currentThesaurus;
    if (data) {
        return {
            word: data.word,
            synonyms: [...data.synonyms],
            confidence: data.confidence,
        };
    }

    if (entry.value?.definitions) {
        const synonyms = (entry.value.definitions as any[])
            .flatMap((d: any) => d.synonyms || [])
            .filter((s: string, i: number, arr: string[]) => arr.indexOf(s) === i)
            .map((word: string) => ({ word, score: 0.8 }));
        if (synonyms.length > 0) {
            return { word: entry.value.word, synonyms, confidence: 0.7 };
        }
    }

    return null;
});

function extractProviderSynonyms(entryData: any, provider: string) {
    const synonymSet = new Set<string>();

    if (entryData.definitions) {
        for (const def of entryData.definitions) {
            if (!def.providers_data) continue;
            const providerEntries = Array.isArray(def.providers_data)
                ? def.providers_data
                : [def.providers_data];

            for (const pd of providerEntries) {
                if (pd.provider !== provider) continue;
                if (pd.definitions) {
                    for (const pDef of pd.definitions) {
                        if (pDef.synonyms) {
                            for (const s of pDef.synonyms) {
                                synonymSet.add(s);
                            }
                        }
                    }
                }
            }
        }
    }

    return Array.from(synonymSet).map((word) => ({ word, score: 1.0 }));
}

// Error and empty state handling
const isEmpty = computed(() => {
    return (
        entry.value &&
        (!entry.value.definitions || entry.value.definitions.length === 0)
    );
});

// Composables
const { usedProviders } = useProviders(entry);
const { allImages, handleImageClick, handleImageError } =
    useImageManagement(entry);
const actions = useDefinitionActions({ entry, editModeEnabled });
const timeMachine = useTimeMachine(computed(() => entry.value?.word));

// Inline word lookup
const definitionCardRef = ref<HTMLElement | null>(null);
const inlineLookup = useInlineWordLookup(definitionCardRef);

// Reactive state bundles for DefinitionModals props
const timeMachineState = computed(() => ({
    isOpen: timeMachine.isOpen.value,
    versions: timeMachine.versions.value,
    selectedIndex: timeMachine.selectedIndex.value,
    selectedVersion: timeMachine.selectedVersion.value,
    versionDetail: timeMachine.versionDetail.value,
    versionDiff: timeMachine.versionDiff.value,
    diffFields: timeMachine.diffFields.value,
    textChanges: timeMachine.textChanges.value,
    hydratedEntry: timeMachine.hydratedEntry.value,
    navigationDirection: timeMachine.navigationDirection.value,
    loading: timeMachine.loading.value,
    detailLoading: timeMachine.detailLoading.value,
    rollingBack: timeMachine.rollingBack.value,
    isNewest: timeMachine.isNewest.value,
    isOldest: timeMachine.isOldest.value,
    expandedView: timeMachine.expandedView.value,
}));

const inlineLookupState = computed(() => ({
    selectedWord: inlineLookup.selectedWord.value,
    isPillVisible: inlineLookup.isPillVisible.value,
    isPopoverVisible: inlineLookup.isPopoverVisible.value,
    position: inlineLookup.position.value,
}));

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

const hasAISynthesis = computed(() => !!entry.value?.model_info);
const selectableSources = computed(() => {
    const sources: string[] = [];
    if (hasAISynthesis.value) {
        sources.push('synthesis');
    }
    sources.push(...usedProviders.value);
    return sources;
});

const sourceSelectionDisabled = computed(() => {
    return selectableSources.value.length <= 1;
});

// Keep source selection valid and auto-lock when only one source exists
watch(
    () => [
        entry.value?.word,
        selectableSources.value.join('|'),
        effectivelyPremium.value,
    ],
    () => {
        const sources = selectableSources.value;
        if (sources.length === 0) {
            activeSourceTab.value = 'synthesis';
            return;
        }

        if (sources.length === 1) {
            activeSourceTab.value = sources[0];
            return;
        }

        if (hasAISynthesis.value && effectivelyPremium.value) {
            activeSourceTab.value = 'synthesis';
            return;
        }

        if (!sources.includes(activeSourceTab.value)) {
            activeSourceTab.value = sources[0];
        }
    },
    { immediate: true },
);

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
