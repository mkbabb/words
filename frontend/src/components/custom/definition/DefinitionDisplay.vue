<template>
    <!-- Error State -->
    <div v-if="store.definitionError?.hasError" class="relative">
        <ThemedCard :variant="store.selectedCardVariant" class="relative">
            <ErrorState 
                :title="getErrorTitle(store.definitionError.errorType)"
                :message="store.definitionError.errorMessage"
                :error-type="store.definitionError.errorType"
                :retryable="store.definitionError.canRetry"
                :show-help="store.definitionError.errorType === 'unknown'"
                @retry="handleRetryLookup"
                @help="handleShowHelp"
            />
        </ThemedCard>
    </div>
    
    <!-- Empty State -->
    <div v-else-if="isEmpty && !isStreaming" class="relative">
        <ThemedCard :variant="store.selectedCardVariant" class="relative">
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
        <ThemedCard :variant="store.selectedCardVariant" class="relative">
            <!-- Theme Selector (includes edit button) -->
            <ThemeSelector 
                v-model="store.selectedCardVariant"
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
            />

            <!-- Progressive Header with Smart Skeletons -->
            <WordHeader 
                v-if="entry.word"
                :word="entry.word"
                :pronunciation="entry.pronunciation"
                :pronunciationMode="store.pronunciationMode"
                :providers="usedProviders"
                :animationType="'typewriter'"
                :animationKey="animationKey"
                :isAISynthesized="!!entry.model_info"
                :isStreaming="isStreaming"
                @toggle-pronunciation="store.togglePronunciation"
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
                    <div :key="store.mode" class="space-y-4">
                        <!-- Dictionary Mode with Progressive Loading -->
                        <template v-if="store.mode === 'dictionary'">
                            <!-- Render available definition clusters -->
                            <DefinitionCluster
                                v-for="(cluster, clusterIndex) in groupedDefinitions"
                                :key="cluster.clusterId"
                                :cluster="cluster"
                                :clusterIndex="clusterIndex"
                                :totalClusters="groupedDefinitions.length"
                                :cardVariant="store.selectedCardVariant"
                                :editModeEnabled="editModeEnabled"
                                :isStreaming="isStreaming"
                                @update:cluster-name="handleClusterNameUpdate"
                            >
                                <DefinitionItem
                                    v-for="(definition, defIndex) in cluster.definitions"
                                    :key="`${cluster.clusterId}-${defIndex}`"
                                    :definition="definition"
                                    :definitionIndex="getGlobalDefinitionIndex(clusterIndex, defIndex)"
                                    :isRegenerating="regeneratingIndex === getGlobalDefinitionIndex(clusterIndex, defIndex)"
                                    :isFirstInGroup="defIndex === 0"
                                    :isAISynthesized="!!entry.model_info"
                                    :editModeEnabled="editModeEnabled"
                                    :isStreaming="isStreaming"
                                    @regenerate="handleRegenerateExamples"
                                    @searchWord="store.searchWord"
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
                        <template v-else-if="store.mode === 'thesaurus'">
                            <ThesaurusView
                                :thesaurusData="store.currentThesaurus"
                                :cardVariant="store.selectedCardVariant"
                                @word-click="store.searchWord"
                            />
                        </template>

                        <!-- AI Suggestions Mode -->
                        <template v-else-if="store.mode === 'suggestions'">
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
import { useAppStore } from '@/stores';
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
import { useDefinitionGroups, useAnimationCycle, useProviders, useImageManagement } from './composables';
import { normalizeEtymology } from '@/utils/guards';
import type { ImageMedia } from '@/types/api';

// Store
const store = useAppStore();

// Reactive state
const regeneratingIndex = ref<number | null>(null);
const animationKey = ref(0);
const isMounted = ref(false);
const showThemeDropdown = ref(false);
const editModeEnabled = ref(false);
const showWordlistModal = ref(false);
const wordToAdd = ref('');

// Smart computed properties - merge streaming and complete data
const entry = computed(() => {
    // If there's an error, don't return entry data
    if (store.definitionError?.hasError) {
        return null;
    }
    
    // When streaming, merge partial data with current entry
    if (store.isStreamingData && store.partialEntry) {
        return {
            // Use partial data as primary source, fallback to current entry
            word: store.partialEntry.word || store.currentEntry?.word,
            id: store.partialEntry.id || store.currentEntry?.id,
            last_updated: store.partialEntry.last_updated || store.currentEntry?.last_updated,
            model_info: store.partialEntry.model_info || store.currentEntry?.model_info,
            pronunciation: store.partialEntry.pronunciation || store.currentEntry?.pronunciation,
            etymology: store.partialEntry.etymology || store.currentEntry?.etymology,
            images: [...(store.partialEntry.images || []), ...(store.currentEntry?.images || [])],
            definitions: store.partialEntry.definitions || store.currentEntry?.definitions || [],
            // Add streaming metadata
            _isStreaming: true,
            _streamingProgress: store.loadingProgress,
        } as any;
    }
    
    // When not streaming, use complete current entry
    return store.currentEntry ? {
        ...store.currentEntry,
        _isStreaming: false,
    } as any : null;
});

// Streaming state indicators
const isStreaming = computed(() => store.isStreamingData);
const hasPartialData = computed(() => !!store.partialEntry);

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
    return store.definitionError?.originalWord 
        ? `No definitions found for "${store.definitionError.originalWord}"`
        : 'No definitions found';
};

const getEmptyMessage = () => {
    return 'This word might not exist in our dictionary, or it could be a specialized term. Try searching for a similar word or check your spelling.';
};

// Force animation key update when word changes
watch(entry, (newEntry, oldEntry) => {
    if (newEntry?.word !== oldEntry?.word) {
        animationKey.value++;
    }
});

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
const { startCycle, stopCycle } = useAnimationCycle(() => animationKey.value++);
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
    if (regeneratingIndex.value !== null) return;
    
    regeneratingIndex.value = definitionIndex;
    try {
        await store.regenerateExamples(definitionIndex);
    } catch (error) {
        console.error('Failed to regenerate examples:', error);
    } finally {
        regeneratingIndex.value = null;
    }
};

// Wrap the base handlers to add any additional logic if needed
const handleImageError = baseHandleImageError;
const handleImageClick = baseHandleImageClick;

const handleImagesUpdated = async (newImages: ImageMedia[]) => {
    console.log('Images updated, refreshing synthesized entry:', newImages);
    
    try {
        // Refresh the synthesized entry to get updated images from the backend
        await store.refreshSynthEntryImages();
    } catch (error) {
        console.error('Failed to refresh entry images:', error);
        // Fallback - still show a success message since the upload itself succeeded
        store.showNotification({
            type: 'warning',
            message: 'Images uploaded but display may not be current. Try refreshing.',
            duration: 5000,
        });
    }
};

const handleClusterNameUpdate = async (clusterId: string, newName: string) => {
    // Find the first definition in this cluster to update
    const definition = entry.value?.definitions?.find(def => 
        def.meaning_cluster?.id === clusterId || 
        def.meaning_cluster?.name === clusterId
    );
    
    if (definition?.id) {
        await store.updateDefinition(definition.id, {
            meaning_cluster_name: newName
        });
    }
};

const handleAddToWordlist = (word: string) => {
    wordToAdd.value = word;
    showWordlistModal.value = true;
};

const handleWordAddedToList = (wordlist: any, word: string) => {
    // Show success notification or handle the addition result
    console.log(`Successfully added "${word}" to wordlist "${wordlist.name}"`);
    // TODO: Show success toast notification
};

// Error handling methods
const handleRetryLookup = () => {
    if (store.definitionError?.originalWord) {
        const wordToRetry = store.definitionError.originalWord;
        // Clear the error state and retry the lookup
        store.definitionError = null;
        store.searchWord(wordToRetry);
    }
};

const handleShowHelp = () => {
    // Show help modal or redirect to help page
    console.log('Show help for definition lookup issues');
    // TODO: Implement help system
};

const handleSuggestAlternatives = () => {
    // Switch to suggestions mode or show alternative suggestions
    store.mode = 'suggestions';
    console.log('Suggesting alternatives for failed lookup');
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

// Watch mode changes to ensure thesaurus data is loaded and trigger animations
watch(() => store.mode, async (newMode, oldMode) => {
    // Trigger animation by incrementing key
    if (oldMode && newMode !== oldMode) {
        animationKey.value++;
    }
    
    if (newMode === 'thesaurus' && entry.value) {
        // Ensure thesaurus data is loaded when switching to thesaurus mode
        await store.getThesaurusData(entry.value.word);
    }
});

// Lifecycle
watch(() => isMounted.value, (mounted) => {
    if (mounted) {
        startCycle();
    } else {
        stopCycle();
    }
}, { immediate: true });

// Set mounted state
isMounted.value = true;

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