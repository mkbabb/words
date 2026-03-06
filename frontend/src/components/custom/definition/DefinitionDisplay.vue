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
    <div v-else-if="entry" class="relative">
        <!-- Main Card -->
        <ThemedCard :variant="selectedCardVariant" class="relative">
            <!-- Theme Selector (includes edit button) -->
            <ThemeSelector
                v-model="selectedCardVariant"
                :isMounted="isMounted"
                :showDropdown="actions.showThemeDropdown.value"
                :editModeEnabled="editModeEnabled"
                @toggle-dropdown="
                    actions.showThemeDropdown.value =
                        !actions.showThemeDropdown.value
                "
                @toggle-edit-mode="editModeEnabled = !editModeEnabled"
                @toggle-version-history="actions.handleToggleVersionHistory"
                @resynthesize="actions.handleReSynthesize"
            />

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
                :isAISynthesized="!!entry.model_info"
                :activeSource="activeSourceTab"
                :sourceSelectionDisabled="sourceSelectionDisabled"
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
                class="h-px border-0 bg-gradient-to-r from-transparent via-muted-foreground/20 to-transparent dark:via-muted-foreground/30"
            />

            <!-- Provider source tabs (AI Synthesis + raw provider data) -->
            <ProviderViewTabs
                v-model="activeSourceTab"
                :word="entry?.word || ''"
                :available-providers="usedProviders"
                :show-synthesis="!!entry?.model_info"
            >
            <!-- Mode Content -->
            <CardContent class="space-y-4 px-4 sm:px-6">
                <Transition name="mode-switch" mode="out-in">
                    <!-- Wrapper div with key that changes on mode switch -->
                    <div
                        :key="searchBar.getSubMode('lookup')"
                        class="space-y-4"
                    >
                        <!-- Dictionary Mode with Progressive Loading -->
                        <template
                            v-if="
                                searchBar.getSubMode('lookup') === 'dictionary'
                            "
                        >
                            <!-- Render available definition clusters -->
                            <DefinitionCluster
                                v-for="(
                                    cluster, clusterIndex
                                ) in groupedDefinitions"
                                :key="cluster.clusterId"
                                :cluster="cluster"
                                :clusterIndex="clusterIndex"
                                :totalClusters="groupedDefinitions.length"
                                :cardVariant="selectedCardVariant"
                                :editModeEnabled="editModeEnabled"
                                :isStreaming="isStreaming"
                                @update:cluster-name="
                                    actions.handleClusterNameUpdate
                                "
                            >
                                <DefinitionItem
                                    v-for="(
                                        definition, defIndex
                                    ) in cluster.definitions"
                                    :key="`${cluster.clusterId}-${defIndex}`"
                                    :definition="definition"
                                    :definitionIndex="
                                        getGlobalDefinitionIndex(
                                            clusterIndex,
                                            defIndex
                                        )
                                    "
                                    :isRegenerating="
                                        contentStore.regeneratingDefinitionIndex ===
                                        getGlobalDefinitionIndex(
                                            clusterIndex,
                                            defIndex
                                        )
                                    "
                                    :isFirstInGroup="defIndex === 0"
                                    :isAISynthesized="!!entry.model_info"
                                    :editModeEnabled="editModeEnabled"
                                    :isStreaming="isStreaming"
                                    :word="entry?.word"
                                    @regenerate="
                                        actions.handleRegenerateExamples
                                    "
                                    @searchWord="actions.handleWordSearch"
                                    @addToWordlist="actions.handleAddToWordlist"
                                />
                            </DefinitionCluster>

                            <!-- Progressive skeleton for expected definitions -->
                            <DefinitionStreamingSkeleton
                                :show="shouldShowDefinitionSkeletons"
                                :count="expectedDefinitionCount"
                            />
                        </template>

                        <!-- Thesaurus Mode -->
                        <template
                            v-else-if="
                                searchBar.getSubMode('lookup') === 'thesaurus'
                            "
                        >
                            <ThesaurusView
                                :thesaurusData="thesaurusData"
                                :cardVariant="selectedCardVariant"
                                @word-click="actions.handleWordSearch"
                                @retry-thesaurus="actions.handleRetryThesaurus"
                                @switch-to-dictionary="searchBar.setSubMode('lookup', 'dictionary')"
                            />
                        </template>

                        <!-- AI Suggestions Mode -->
                        <template
                            v-else-if="
                                searchBar.getSubMode('lookup') === 'suggestions'
                            "
                        >
                            <!-- This mode is handled by WordSuggestionDisplay in Home.vue -->
                            <div class="text-center text-muted-foreground">
                                Switching to suggestions mode...
                            </div>
                        </template>
                    </div>
                </Transition>
            </CardContent>

            <!-- Progressive Etymology -->
            <div v-if="normalizedEtymology" data-cluster-id="etymology">
                <Etymology :etymology="normalizedEtymology" />
            </div>
            <!-- Etymology Skeleton -->
            <div
                v-else-if="isStreaming && !normalizedEtymology"
                class="animate-pulse border-t p-6"
            >
                <div class="mb-4 h-6 w-24 rounded bg-muted" />
                <div class="space-y-2">
                    <div class="h-4 w-full rounded bg-muted" />
                    <div class="h-4 w-2/3 rounded bg-muted" />
                </div>
            </div>

            <!-- Debug Info with Streaming Status -->
            <div v-if="entry.id" class="mt-4 flex justify-center">
                <div
                    class="flex items-center gap-2 rounded-md border border-border/30 bg-background/50 px-3 py-1 text-xs text-muted-foreground/50"
                >
                    {{ entry.id }}
                    <div v-if="isStreaming" class="flex items-center gap-1">
                        <div
                            class="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500"
                        />
                        <span class="text-blue-500">streaming</span>
                    </div>
                </div>
            </div>
            </ProviderViewTabs>
        </ThemedCard>

        <!-- Version History Panel (admin only) -->
        <div
            v-if="actions.showVersionHistory.value && entry?.word"
            class="mt-4 rounded-lg border border-border bg-background p-4"
        >
            <VersionHistory
                :word="entry.word"
                :currentVersion="entry.version"
                @close="actions.handleToggleVersionHistory"
                @rollback="handleVersionRollback"
            />
        </div>

        <!-- Add to Wordlist Modal -->
        <AddToWordlistModal
            v-model="actions.showWordlistModal.value"
            :word="actions.wordToAdd.value"
            @added="actions.handleWordAddedToList"
        />
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useContentStore } from '@/stores';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';
import { CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
    ThemeSelector,
    WordHeader,
    DefinitionCluster,
    DefinitionItem,
    ThesaurusView,
    Etymology,
    ImageCarousel,
    ErrorState,
    EmptyState,
} from './components';
import DefinitionStreamingSkeleton from './skeletons/DefinitionStreamingSkeleton.vue';
import { ThemedCard } from '@/components/custom/card';
import AddToWordlistModal from './components/AddToWordlistModal.vue';
import ProviderViewTabs from './components/ProviderViewTabs.vue';
import VersionHistory from './components/VersionHistory.vue';
import {
    useDefinitionGroups,
    useProviders,
    useImageManagement,
    useDefinitionActions,
} from './composables';
import {
    getErrorTitle,
    getEmptyTitle,
    getEmptyMessage,
} from './utils/stateMessages';
import { normalizeEtymology } from '@/utils/guards';
import { useAuthStore } from '@/stores/auth';

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
const activeSourceTab = ref('synthesis');

// In dev mode, treat user as premium (matching backend's admin passthrough)
const effectivelyPremium = computed(() =>
    authStore.isPremium || import.meta.env.DEV
);

// Smart computed properties - merge streaming and complete data
const entry = computed(() => {
    // If there's an error, don't return entry data
    if (contentStore.definitionError?.hasError) {
        return null;
    }

    // When streaming, merge partial data with current entry
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
            _isStreaming: true,
            _streamingProgress: 0,
        } as any;
    }

    // When not streaming, use complete current entry
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

// Convert readonly thesaurus to mutable type for component compatibility
const thesaurusData = computed(() => {
    const data = contentStore.currentThesaurus;
    if (data) {
        return {
            word: data.word,
            synonyms: [...data.synonyms],
            confidence: data.confidence,
        };
    }

    // Fallback: extract synonyms from provider definitions (useful in no_ai mode)
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

// Smart skeleton logic
const expectedDefinitionCount = computed(() => {
    if (isStreaming.value) {
        const currentCount = entry.value?.definitions?.length || 0;
        const estimatedTotal = Math.max(3, currentCount + 1);
        return Math.min(estimatedTotal - currentCount, 3);
    }
    return 0;
});

const shouldShowDefinitionSkeletons = computed(() => {
    return isStreaming.value && expectedDefinitionCount.value > 0;
});

// Error and empty state handling
const isEmpty = computed(() => {
    return (
        entry.value &&
        (!entry.value.definitions || entry.value.definitions.length === 0)
    );
});

const normalizedEtymology = computed(() => {
    return normalizeEtymology(entry.value?.etymology);
});

// Composables
const { groupedDefinitions } = useDefinitionGroups(entry);
const { usedProviders } = useProviders(entry);
const { allImages, handleImageClick, handleImageError } =
    useImageManagement(entry);
const actions = useDefinitionActions({ entry, editModeEnabled });

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

// Version rollback handler: re-fetch the word after rollback
const handleVersionRollback = async (_version: string) => {
    if (entry.value?.word) {
        // Re-fetch the word to get the rolled-back version
        const orchestrator2 = useSearchOrchestrator({
            query: computed(() => entry.value?.word || ''),
        });
        try {
            await orchestrator2.getDefinition(entry.value.word);
        } catch {
            // Silently fail — user can manually refresh
        }
        actions.showVersionHistory.value = false;
    }
};

// Helpers
const getGlobalDefinitionIndex = (
    clusterIndex: number,
    defIndex: number
): number => {
    let globalIndex = 0;
    for (let i = 0; i < clusterIndex; i++) {
        globalIndex += groupedDefinitions.value[i].definitions.length;
    }
    return globalIndex + defIndex;
};
</script>

<style scoped>
/* Mode switch transitions - Apple-style with bounce */
.mode-switch-enter-active {
    transition: opacity 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275), transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); /* apple-spring */
}

.mode-switch-leave-active {
    transition: opacity 0.25s cubic-bezier(0.6, -0.28, 0.735, 0.045), transform 0.25s cubic-bezier(0.6, -0.28, 0.735, 0.045); /* apple-bounce-in */
}

.mode-switch-enter-from {
    opacity: 0;
    transform: scale(0.9) translateX(30px) rotate(2deg);
}

.mode-switch-enter-to {
    opacity: 1;
    transform: scale(1) translateX(0) rotate(0);
}

.mode-switch-leave-from {
    opacity: 1;
    transform: scale(1) translateX(0) rotate(0);
}

.mode-switch-leave-to {
    opacity: 0;
    transform: scale(0.9) translateX(-30px) rotate(-2deg);
}

/* Themed gradients and hover effects */
.themed-hr {
    background: linear-gradient(
        to right,
        transparent,
        var(--border) 20%,
        var(--border) 80%,
        transparent
    );
}

/* Ensure proper stacking context */
.sticky {
    will-change: transform;
}
</style>
