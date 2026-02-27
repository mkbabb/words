<template>
    <!-- Error State -->
    <div v-if="contentStore.definitionError?.hasError" class="relative">
        <ThemedCard :variant="selectedCardVariant" class="relative">
            <ErrorState 
                :title="getErrorTitle(contentStore.definitionError.errorType)"
                :message="contentStore.definitionError.errorMessage"
                :error-type="contentStore.definitionError.errorType"
                :retryable="contentStore.definitionError.canRetry"
                :show-help="contentStore.definitionError.errorType === 'unknown'"
                @retry="handleRetryLookup"
                @help="handleShowHelp"
            />
        </ThemedCard>
    </div>
    
    <!-- Empty State -->
    <div v-else-if="isEmpty && !isStreaming" class="relative">
        <ThemedCard :variant="selectedCardVariant" class="relative">
            <EmptyState
                :title="getEmptyTitle()"
                :message="getEmptyMessage()"
                empty-type="no-definitions"
                :show-suggestions="true"
                @suggest-alternatives="handleSuggestAlternatives"
            >
                <template #actions>
                    <div class="flex items-center gap-3">
                        <Button 
                            @click="handleRetryLookup"
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
                :showDropdown="showThemeDropdown"
                :editModeEnabled="editModeEnabled"
                @toggle-dropdown="showThemeDropdown = !showThemeDropdown"
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
                @images-updated="handleImagesUpdated"
                @image-deleted="handleImageDeleted"
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
                    <div class="h-8 w-48 bg-muted rounded animate-pulse" />
                    <div class="h-8 w-24 bg-muted rounded animate-pulse" />
                </div>
                <div class="flex items-center gap-4">
                    <div class="h-6 w-32 bg-muted rounded animate-pulse" />
                    <div class="h-5 w-16 bg-muted rounded animate-pulse" />
                </div>
            </div>

            <!-- Gradient Separator -->
            <hr class="border-0 h-px bg-gradient-to-r from-transparent via-muted-foreground/20 to-transparent dark:via-muted-foreground/30" />

            <!-- Mode Content -->
            <CardContent class="space-y-4 px-4 sm:px-6">
                <Transition
                    name="mode-switch"
                    mode="out-in"
                >
                    <!-- Wrapper div with key that changes on mode switch -->
                    <div :key="searchBar.getSubMode('lookup')" class="space-y-4">
                        <!-- Dictionary Mode with Progressive Loading -->
                        <template v-if="searchBar.getSubMode('lookup') === 'dictionary'">
                            <!-- Render available definition clusters -->
                            <DefinitionCluster
                                v-for="(cluster, clusterIndex) in groupedDefinitions"
                                :key="cluster.clusterId"
                                :cluster="cluster"
                                :clusterIndex="clusterIndex"
                                :totalClusters="groupedDefinitions.length"
                                :cardVariant="selectedCardVariant"
                                :editModeEnabled="editModeEnabled"
                                :isStreaming="isStreaming"
                                @update:cluster-name="handleClusterNameUpdate"
                            >
                                <DefinitionItem
                                    v-for="(definition, defIndex) in cluster.definitions"
                                    :key="`${cluster.clusterId}-${defIndex}`"
                                    :definition="definition"
                                    :definitionIndex="getGlobalDefinitionIndex(clusterIndex, defIndex)"
                                    :isRegenerating="contentStore.regeneratingDefinitionIndex === getGlobalDefinitionIndex(clusterIndex, defIndex)"
                                    :isFirstInGroup="defIndex === 0"
                                    :isAISynthesized="!!entry.model_info"
                                    :editModeEnabled="editModeEnabled"
                                    :isStreaming="isStreaming"
                                    @regenerate="handleRegenerateExamples"
                                    @searchWord="handleWordSearch"
                                    @addToWordlist="handleAddToWordlist"
                                />
                            </DefinitionCluster>
                            
                            <!-- Progressive skeleton for expected definitions -->
                            <div v-if="isStreaming && shouldShowDefinitionSkeletons" class="space-y-6">
                                <div v-for="i in expectedDefinitionCount" :key="`skeleton-${i}`" class="border-l-2 border-accent pl-4 space-y-3 animate-pulse">
                                    <div class="flex items-center gap-2">
                                        <div class="h-5 w-16 bg-muted rounded" />
                                        <div class="h-4 w-8 bg-muted rounded" />
                                    </div>
                                    <div class="space-y-2">
                                        <div class="h-6 w-full bg-muted rounded" />
                                        <div class="h-4 w-4/5 bg-muted rounded" />
                                    </div>
                                    <div class="flex flex-wrap gap-1">
                                        <div v-for="j in 4" :key="j" class="h-6 w-16 bg-muted rounded" />
                                    </div>
                                </div>
                            </div>
                        </template>

                        <!-- Thesaurus Mode -->
                        <template v-else-if="searchBar.getSubMode('lookup') === 'thesaurus'">
                            <ThesaurusView
                                :thesaurusData="thesaurusData"
                                :cardVariant="selectedCardVariant"
                                @word-click="handleWordSearch"
                                @retry-thesaurus="handleRetryThesaurus"
                            />
                        </template>

                        <!-- AI Suggestions Mode -->
                        <template v-else-if="searchBar.getSubMode('lookup') === 'suggestions'">
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
            <div v-else-if="isStreaming && !normalizedEtymology" class="p-6 border-t animate-pulse">
                <div class="h-6 w-24 bg-muted rounded mb-4" />
                <div class="space-y-2">
                    <div class="h-4 w-full bg-muted rounded" />
                    <div class="h-4 w-2/3 bg-muted rounded" />
                </div>
            </div>
            
            <!-- Debug Info with Streaming Status -->
            <div v-if="entry.id" class="flex justify-center mt-4">
                <div class="text-xs text-muted-foreground/50 px-3 py-1 border border-border/30 rounded-md bg-background/50 flex items-center gap-2">
                    {{ entry.id }}
                    <div v-if="isStreaming" class="flex items-center gap-1">
                        <div class="h-1.5 w-1.5 bg-blue-500 rounded-full animate-pulse" />
                        <span class="text-blue-500">streaming</span>
                    </div>
                </div>
            </div>
        </ThemedCard>
        
        <!-- Wordlist Selection Modal -->
        <WordlistSelectionModal
            v-model="showWordlistModal"
            :word="wordToAdd"
            @word-added="handleWordAddedToList"
        />
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useMagicKeys, whenever } from '@vueuse/core';
import { useContentStore, useNotificationStore } from '@/stores';
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
    EmptyState
} from './components';
import { ThemedCard } from '@/components/custom/card';
import { WordlistSelectionModal } from '@/components/custom/wordlist';
import { useDefinitionGroups, useProviders, useImageManagement } from './composables';
import { normalizeEtymology } from '@/utils/guards';
import { logger } from '@/utils/logger';
import type { ImageMedia } from '@/types/api';

// Stores
const contentStore = useContentStore();
const notificationStore = useNotificationStore();
const lookupMode = useLookupMode();
const searchBar = useSearchBarStore();

// Orchestrator for API operations
const orchestrator = useSearchOrchestrator({
    query: computed(() => searchBar.searchQuery)
});

// Reactive state
const isMounted = ref(true);
const editModeEnabled = ref(false);
const showWordlistModal = ref(false);
const wordToAdd = ref('');
const showThemeDropdown = ref(false);

// Use UI store state for regeneration
// const regeneratingIndex = computed(() => ui.regeneratingIndex); // Used in template

// Smart computed properties - merge streaming and complete data
const entry = computed(() => {
    // If there's an error, don't return entry data
    if (contentStore.definitionError?.hasError) {
        return null;
    }
    
    // When streaming, merge partial data with current entry
    if (contentStore.isStreamingData && contentStore.partialEntry) {
        return {
            // Use partial data as primary source, fallback to current entry
            word: contentStore.partialEntry.word || contentStore.currentEntry?.word,
            id: contentStore.partialEntry.id || contentStore.currentEntry?.id,
            last_updated: contentStore.partialEntry.last_updated || contentStore.currentEntry?.last_updated,
            model_info: contentStore.partialEntry.model_info || contentStore.currentEntry?.model_info,
            pronunciation: contentStore.partialEntry.pronunciation || contentStore.currentEntry?.pronunciation,
            etymology: contentStore.partialEntry.etymology || contentStore.currentEntry?.etymology,
            images: [...(contentStore.partialEntry.images || []), ...(contentStore.currentEntry?.images || [])],
            definitions: contentStore.partialEntry.definitions || contentStore.currentEntry?.definitions || [],
            // Add streaming metadata
            _isStreaming: true,
            _streamingProgress: 0, // We'll need to get this from loading store if needed
        } as any;
    }
    
    // When not streaming, use complete current entry
    return contentStore.currentEntry ? {
        ...contentStore.currentEntry,
        _isStreaming: false,
    } as any : null;
});

// Streaming state indicators
const isStreaming = computed(() => contentStore.isStreamingData);
// const hasPartialData = computed(() => !!contentStore.partialEntry);

// UI State computed properties
const selectedCardVariant = computed({
    get: () => lookupMode.selectedCardVariant,
    set: (value) => lookupMode.setCardVariant(value)
});

// Convert readonly thesaurus to mutable type for component compatibility
const thesaurusData = computed(() => {
    const data = contentStore.currentThesaurus;
    if (!data) return null;
    return {
        word: data.word,
        synonyms: [...data.synonyms], // Convert readonly array to mutable
        confidence: data.confidence
    };
});

// Smart skeleton logic
const expectedDefinitionCount = computed(() => {
    // Show skeletons based on typical word complexity or progress hints
    if (isStreaming.value) {
        const currentCount = entry.value?.definitions?.length || 0;
        const estimatedTotal = Math.max(3, currentCount + 1); // Always show at least 1 more
        return Math.min(estimatedTotal - currentCount, 3); // Cap at 3 skeletons
    }
    return 0;
});

const shouldShowDefinitionSkeletons = computed(() => {
    return isStreaming.value && expectedDefinitionCount.value > 0;
});

// Error and empty state handling
const isEmpty = computed(() => {
    return entry.value && (!entry.value.definitions || entry.value.definitions.length === 0);
});

const getErrorTitle = (errorType: string) => {
    switch (errorType) {
        case 'network':
            return 'Connection Error';
        case 'not-found':
            return 'Word Not Found';
        case 'server':
            return 'Server Error';
        case 'ai-failed':
            return 'AI Processing Failed';
        case 'empty':
            return 'No Definitions Found';
        default:
            return 'Something Went Wrong';
    }
};

const getEmptyTitle = () => {
    return contentStore.definitionError?.originalWord 
        ? `No definitions found for "${contentStore.definitionError.originalWord}"`
        : 'No definitions found';
};

const getEmptyMessage = () => {
    return 'This word might not exist in our dictionary, or it could be a specialized term. Try searching for a similar word or check your spelling.';
};


// Clean up debug logging
// watch(() => store.definitionError, (newError, oldError) => {
//     console.log('DefinitionDisplay: definitionError changed', { 
//         old: oldError, 
//         new: newError,
//         hasError: newError?.hasError 
//     });
// }, { deep: true, immediate: true });

const normalizedEtymology = computed(() => {
    return normalizeEtymology(entry.value?.etymology);
});

// Composables
const { groupedDefinitions } = useDefinitionGroups(entry);
const { usedProviders } = useProviders(entry);
const { allImages, handleImageClick: baseHandleImageClick, handleImageError: baseHandleImageError } = useImageManagement(entry);



// Helpers
const getGlobalDefinitionIndex = (clusterIndex: number, defIndex: number): number => {
    let globalIndex = 0;
    for (let i = 0; i < clusterIndex; i++) {
        globalIndex += groupedDefinitions.value[i].definitions.length;
    }
    return globalIndex + defIndex;
};

// Event handlers
const handleRegenerateExamples = async (definitionIndex: number) => {
    try {
        await contentStore.regenerateExamples(definitionIndex);
    } catch (error) {
        logger.error('Failed to regenerate examples:', error);
    }
};

// Wrap the base handlers to add any additional logic if needed
const handleImageError = baseHandleImageError;
const handleImageClick = baseHandleImageClick;

const handleImagesUpdated = async (_newImages: ImageMedia[]) => {
    try {
        // Refresh the synthesized entry to get updated images from the backend
        await contentStore.refreshEntryImages();
    } catch (error) {
        logger.error('Failed to refresh entry images:', error);
        // Fallback - still show a success message since the upload itself succeeded
        notificationStore.showNotification({
            type: 'warning',
            message: 'Images uploaded but display may not be current. Try refreshing.',
            duration: 5000,
        });
    }
};

const handleImageDeleted = async (_imageId: string) => {
    try {
        // Refresh the synthesized entry to remove the deleted image reference
        await contentStore.refreshEntryImages();
        
        notificationStore.showNotification({
            type: 'success',
            message: 'Image deleted successfully',
            duration: 3000,
        });
    } catch (error) {
        logger.error('Failed to refresh entry after image deletion:', error);
        notificationStore.showNotification({
            type: 'error',
            message: 'Image deleted but display may not be current. Try refreshing.',
            duration: 5000,
        });
    }
};

const handleClusterNameUpdate = async (clusterId: string, newName: string) => {
    // Find the first definition in this cluster to update
    const definition = entry.value?.definitions?.find((def: any) => 
        def.meaning_cluster?.id === clusterId || 
        def.meaning_cluster?.name === clusterId
    );
    
    if (definition?.id) {
        await contentStore.updateDefinition(definition.id, {
            meaning_cluster: {
                ...definition.meaning_cluster,
                name: newName
            } as any
        });
    }
};

const handleWordSearch = (_word: string) => {
    // This should trigger a search for the new word
    // We'll emit this to parent or handle through router
    // TODO: Implement word search navigation
};

const handleAddToWordlist = (word: string) => {
    wordToAdd.value = word;
    showWordlistModal.value = true;
};

const handleWordAddedToList = (_wordlist: any, _word: string) => {
    // Show success notification or handle the addition result
    // TODO: Show success toast notification
};

// Error handling methods
const handleRetryLookup = () => {
    if (contentStore.definitionError?.originalWord) {
        const wordToRetry = contentStore.definitionError.originalWord;
        // Clear the error state and retry the lookup
        contentStore.clearError();
        handleWordSearch(wordToRetry);
    }
};

const handleShowHelp = () => {
    // Show help modal or redirect to help page
    // TODO: Implement help system
};

const handleSuggestAlternatives = () => {
    // Switch to suggestions mode or show alternative suggestions
    searchBar.setSubMode('lookup', 'suggestions');
};

const handleRetryThesaurus = async () => {
    if (entry.value?.word) {
        try {
            await orchestrator.getThesaurusData(entry.value.word);
        } catch (error) {
            logger.error('Failed to retry thesaurus lookup:', error);
            notificationStore.showNotification({
                type: 'error',
                message: 'Failed to load thesaurus data. Please try again.',
                duration: 3000
            });
        }
    }
};

// Keyboard shortcuts using VueUse magic keys
const keys = useMagicKeys();

// Toggle edit mode with Cmd/Ctrl + E
whenever(keys.cmd_e, () => {
    editModeEnabled.value = !editModeEnabled.value;
});
whenever(keys.ctrl_e, () => {
    editModeEnabled.value = !editModeEnabled.value;
});

// Exit edit mode with Escape
whenever(keys.escape, () => {
    if (editModeEnabled.value) {
        editModeEnabled.value = false;
        // Trigger save when exiting edit mode
        saveAllChanges();
    }
});

// Navigation with arrow keys
whenever(keys.arrowdown, () => {
    if (entry.value?.definitions) {
        document.dispatchEvent(new CustomEvent('navigate-definition', { 
            detail: { direction: 'next' } 
        }));
    }
});
whenever(keys.arrowup, () => {
    if (entry.value?.definitions) {
        document.dispatchEvent(new CustomEvent('navigate-definition', { 
            detail: { direction: 'prev' } 
        }));
    }
});

// Save all changes function
const saveAllChanges = () => {
    // Emit a global save event that all EditableField components can listen to
    document.dispatchEvent(new CustomEvent('save-all-edits'));
};

// Watch mode changes to ensure thesaurus data is loaded
watch(() => searchBar.getSubMode('lookup'), async (newMode) => {
    if (newMode === 'thesaurus' && entry.value) {
        // Ensure thesaurus data is loaded when switching to thesaurus mode
        await orchestrator.getThesaurusData(entry.value.word);
    }
});


// Watch edit mode changes to save
watch(editModeEnabled, (newVal, oldVal) => {
    if (oldVal && !newVal) {
        // Save when turning off edit mode
        saveAllChanges();
    }
});
</script>

<style scoped>
/* Mode switch transitions - Apple-style with bounce */
.mode-switch-enter-active {
    transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); /* apple-spring */
}

.mode-switch-leave-active {
    transition: all 0.25s cubic-bezier(0.6, -0.28, 0.735, 0.045); /* apple-bounce-in */
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