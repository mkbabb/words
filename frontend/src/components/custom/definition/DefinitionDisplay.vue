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
                v-if="entry.word"
                :word="entry.word"
                :pronunciation="entry.pronunciation"
                :pronunciationMode="lookupMode.pronunciationMode"
                :providers="usedProviders"
                :isAISynthesized="!!entry.model_info"
                @toggle-pronunciation="lookupMode.togglePronunciation"
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
        </ThemedCard>

        <!-- Add to Wordlist Modal -->
        <AddToWordlistModal
            v-model="actions.showWordlistModal.value"
            :word="actions.wordToAdd.value"
            @added="actions.handleWordAddedToList"
        />
    </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useContentStore } from '@/stores';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { useSearchBarStore } from '@/stores/search/search-bar';
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

// Stores
const contentStore = useContentStore();
const lookupMode = useLookupMode();
const searchBar = useSearchBarStore();

// Reactive state
const isMounted = ref(true);
const editModeEnabled = ref(false);

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
    if (!data) return null;
    return {
        word: data.word,
        synonyms: [...data.synonyms],
        confidence: data.confidence,
    };
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
