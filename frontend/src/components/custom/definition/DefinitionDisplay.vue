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
                'relative transition-all duration-300',
                editModeEnabled && 'ring-1 ring-inset ring-muted-foreground/15',
            ]"
        >
            <!-- Theme Selector (includes edit button) -->
            <ThemeSelector
                v-model="selectedCardVariant"
                :isMounted="isMounted"
                :showDropdown="actions.showThemeDropdown.value"
                :editModeEnabled="editModeEnabled"
                :word="entry?.word"
                :currentVersion="entry?.version"
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
                :sourceEntries="entry?.source_entries"
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
                class="mt-1 mb-1 h-px border-0 bg-gradient-to-r from-transparent via-muted-foreground/20 to-transparent dark:via-muted-foreground/30"
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
            <!-- Mode Content -->
            <CardContent class="space-y-4 px-4 sm:px-6">
                <Transition name="mode-switch" mode="out-in">
                    <!-- Wrapper div with key that changes on mode switch -->
                    <div
                        :key="searchBar.getSubMode('lookup')"
                        class="space-y-4"
                    >
                        <!-- Dictionary Mode with Virtual Windowing -->
                        <template
                            v-if="
                                searchBar.getSubMode('lookup') === 'dictionary'
                            "
                        >
                            <div ref="clusterContainerRef">
                            <!-- Top spacer for virtualized clusters -->
                            <div :style="{ height: topSpacerPx + 'px' }" />

                            <!-- Render only visible definition clusters -->
                            <DefinitionCluster
                                v-for="(item, visIdx) in visibleItems"
                                :key="item.cluster.clusterId"
                                :ref="(el: any) => measureSection(item.id, el?.$el)"
                                :class="clusterAnimReady ? 'animate-cluster-in' : ''"
                                :style="clusterAnimReady ? { animationDelay: `${visIdx * 60}ms` } : undefined"
                                :cluster="item.cluster"
                                :clusterIndex="item.index"
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
                                    ) in item.cluster.definitions"
                                    :key="`${item.cluster.clusterId}-${defIndex}`"
                                    :definition="definition"
                                    :definitionIndex="
                                        getGlobalDefinitionIndex(
                                            item.index,
                                            defIndex
                                        )
                                    "
                                    :isRegenerating="
                                        contentStore.regeneratingDefinitionIndex ===
                                        getGlobalDefinitionIndex(
                                            item.index,
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

                            <!-- Bottom spacer for virtualized clusters -->
                            <div :style="{ height: bottomSpacerPx + 'px' }" />
                            </div>

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
                                :activeSource="activeSourceTab"
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
            <div v-if="normalizedEtymology" id="etymology" data-cluster-id="etymology">
                <Etymology :etymology="normalizedEtymology" :edit-mode-enabled="editModeEnabled" />
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

            <!-- Synonym Chooser (comparative essay) -->
            <SynonymChooserComponent
                v-if="entry.synonym_chooser"
                :synonym-chooser="entry.synonym_chooser"
                @search-word="actions.handleWordSearch"
            />

            <!-- Phrases & Idioms -->
            <PhrasesSection
                v-if="entry.phrases?.length"
                :phrases="entry.phrases"
            />

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

        <!-- Time Machine Version History Overlay -->
        <TimeMachineOverlay
            :is-open="timeMachine.isOpen.value"
            :word="entry?.word"
            :current-version="entry?.version"
            :versions="timeMachine.versions.value"
            :selected-index="timeMachine.selectedIndex.value"
            :selected-version="timeMachine.selectedVersion.value"
            :version-detail="timeMachine.versionDetail.value"
            :version-diff="timeMachine.versionDiff.value"
            :diff-fields="timeMachine.diffFields.value"
            :text-changes="timeMachine.textChanges.value"
            :hydrated-entry="timeMachine.hydratedEntry.value"
            :navigation-direction="timeMachine.navigationDirection.value"
            :loading="timeMachine.loading.value"
            :detail-loading="timeMachine.detailLoading.value"
            :rolling-back="timeMachine.rollingBack.value"
            :is-newest="timeMachine.isNewest.value"
            :is-oldest="timeMachine.isOldest.value"
            :expanded-view="timeMachine.expandedView.value"
            @close="handleTimeMachineClose"
            @select-version="timeMachine.selectVersion"
            @navigate-next="timeMachine.navigateNext"
            @navigate-prev="timeMachine.navigatePrev"
            @rollback="handleTimeMachineRollback"
            @toggle-expanded="timeMachine.toggleExpanded"
        />

        <!-- Inline Word Lookup Popover -->
        <WordLookupPopover
            :selected-word="inlineLookup.selectedWord.value"
            :is-pill-visible="inlineLookup.isPillVisible.value"
            :is-popover-visible="inlineLookup.isPopoverVisible.value"
            :position="inlineLookup.position.value"
            @show-popover="inlineLookup.showPopover"
            @dismiss="inlineLookup.dismiss"
            @lookup="handleInlineLookup"
            @add-to-wordlist="handleInlineAddToWordlist"
        />

        <!-- Add to Wordlist Modal -->
        <AddToWordlistModal
            v-model="actions.showWordlistModal.value"
            :word="actions.wordToAdd.value"
            @added="actions.handleWordAddedToList"
        />
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, provide } from 'vue';
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
import TimeMachineOverlay from './components/TimeMachineOverlay.vue';
import {
    useDefinitionGroups,
    useProviders,
    useImageManagement,
    useDefinitionActions,
    useTimeMachine,
    useVirtualSectionWindow,
    flattenDefinitionClusters,
} from './composables';
import {
    getErrorTitle,
    getEmptyTitle,
    getEmptyMessage,
} from './utils/stateMessages';
import { normalizeEtymology } from '@/utils/guards';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';
import { useInlineWordLookup } from '@/composables/useInlineWordLookup';
import WordLookupPopover from './components/WordLookupPopover.vue';
import SynonymChooserComponent from './components/SynonymChooser.vue';
import PhrasesSection from './components/PhrasesSection.vue';

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
            source_entries:
                contentStore.currentEntry?.source_entries ||
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
// When a specific provider is selected (non-synthesis), show that provider's raw synonyms
const thesaurusData = computed(() => {
    const currentSource = activeSourceTab.value;

    // If a non-synthesis provider is selected, extract synonyms from that provider's data
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

    // Default: use AI-synthesized thesaurus data
    const data = contentStore.currentThesaurus;
    if (data) {
        return {
            word: data.word,
            synonyms: [...data.synonyms],
            confidence: data.confidence,
        };
    }

    // Fallback: extract synonyms from all provider definitions (useful in no_ai mode)
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

// Extract synonyms from a specific provider's raw data
function extractProviderSynonyms(entryData: any, provider: string) {
    const synonymSet = new Set<string>();

    // Check providers_data on each definition
    if (entryData.definitions) {
        for (const def of entryData.definitions) {
            if (!def.providers_data) continue;
            const providerEntries = Array.isArray(def.providers_data)
                ? def.providers_data
                : [def.providers_data];

            for (const pd of providerEntries) {
                if (pd.provider !== provider) continue;
                // Extract synonyms from provider's definitions
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

// Virtual windowing for definition clusters
const clusterContainerRef = ref<HTMLElement | null>(null);
const flatClusters = computed(() => flattenDefinitionClusters(groupedDefinitions.value));
const {
    visibleItems,
    topSpacerPx,
    bottomSpacerPx,
    measureSection,
    ensureTargetWindow,
} = useVirtualSectionWindow({
    items: flatClusters,
    scrollContainer: ref(null), // null = use window/document scroll
    contentEl: clusterContainerRef,
    overscanBeforePx: 400,
    overscanAfterPx: 800,
});

// Provide ensureTargetWindow for sidebar navigation (via provide/inject)
provide('ensureTargetWindow', ensureTargetWindow);

const { usedProviders } = useProviders(entry);
const { allImages, handleImageClick, handleImageError } =
    useImageManagement(entry);
const actions = useDefinitionActions({ entry, editModeEnabled });
const timeMachine = useTimeMachine(computed(() => entry.value?.word));

// Inline word lookup — uses the entire definition card as container
// so it works for both synthesized (cluster view) and raw provider entries
const definitionCardRef = ref<HTMLElement | null>(null);
const inlineLookup = useInlineWordLookup(definitionCardRef);

// Router captured in setup context — safe to use from event handlers
const router = useRouter();

function handleInlineLookup(word: string) {
    inlineLookup.dismiss();
    // Navigate directly — don't go through useRouterSync which calls inject() lazily
    router.push({ name: 'Definition', params: { word } });
}

function handleInlineAddToWordlist(word: string) {
    inlineLookup.dismiss();
    actions.handleAddToWordlist(word);
}

// Wire up the toggle: open Time Machine instead of old panel
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
    // Re-fetch the word to get the rolled-back version
    if (entry.value?.word) {
        const orchestrator2 = useSearchOrchestrator({
            query: computed(() => entry.value?.word || ''),
        });
        try {
            await orchestrator2.getDefinition(entry.value.word);
        } catch {
            // Silently fail — user can manually refresh
        }
    }
};

// --- Staggered cluster entrance animation (CSS class toggle) ---
// Tracks whether the current clusters should animate in (after word change, not initial load)
const clusterAnimReady = ref(false);

// When the word changes, enable animation for the incoming clusters
watch(
    () => entry.value?.word,
    (newWord, oldWord) => {
        if (newWord && oldWord && newWord !== oldWord) {
            clusterAnimReady.value = true;
            // Disable after the animation plays so scroll-virtualized items don't re-animate
            setTimeout(() => { clusterAnimReady.value = false; }, 600);
        }
    },
);

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
/* Mode switch transitions — fade + horizontal slide */
.mode-switch-enter-active {
    transition: opacity 0.25s var(--ease-apple-smooth), transform 0.25s var(--ease-apple-smooth);
}

.mode-switch-leave-active {
    transition: opacity 0.15s var(--ease-apple-default), transform 0.15s var(--ease-apple-default);
}

.mode-switch-enter-from {
    opacity: 0;
    transform: translateX(16px);
}

.mode-switch-enter-to {
    opacity: 1;
    transform: translateX(0);
}

.mode-switch-leave-from {
    opacity: 1;
    transform: translateX(0);
}

.mode-switch-leave-to {
    opacity: 0;
    transform: translateX(-16px);
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

/* Staggered cluster entrance on word change */
@keyframes clusterSlideIn {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}
.animate-cluster-in {
    animation: clusterSlideIn 0.3s ease both;
}
</style>
