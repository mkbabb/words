<template>
    <div v-if="entry" class="relative">
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
                :synthEntryId="entry.synth_entry_id || undefined"
                @image-error="handleImageError"
                @image-click="handleImageClick"
                @images-updated="handleImagesUpdated"
            />

            <!-- Header -->
            <WordHeader 
                :word="entry.word"
                :pronunciation="entry.pronunciation"
                :pronunciationMode="store.pronunciationMode"
                :providers="usedProviders"
                :animationType="'typewriter'"
                :animationKey="animationKey"
                :isAISynthesized="!!entry.model_info"
                @toggle-pronunciation="store.togglePronunciation"
            />

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
                        <!-- Dictionary Mode -->
                        <template v-if="store.mode === 'dictionary'">
                            <DefinitionCluster
                                v-for="(cluster, clusterIndex) in groupedDefinitions"
                                :key="cluster.clusterId"
                                :cluster="cluster"
                                :clusterIndex="clusterIndex"
                                :totalClusters="groupedDefinitions.length"
                                :cardVariant="store.selectedCardVariant"
                                :editModeEnabled="editModeEnabled"
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
                                    @regenerate="handleRegenerateExamples"
                                    @searchWord="store.searchWord"
                                    @addToWordlist="handleAddToWordlist"
                                />
                            </DefinitionCluster>
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

            <!-- Etymology -->
            <div v-if="normalizedEtymology" data-cluster-id="etymology">
                <Etymology :etymology="normalizedEtymology" />
            </div>
            
            <!-- Synth Entry ID (for debugging) -->
            <div v-if="entry.synth_entry_id" class="flex justify-center mt-4">
                <div class="text-xs text-muted-foreground/50 px-3 py-1 border border-border/30 rounded-md bg-background/50">
                    {{ entry.synth_entry_id }}
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
import {
    ThemeSelector,
    WordHeader,
    DefinitionCluster,
    DefinitionItem,
    ThesaurusView,
    Etymology,
    ImageCarousel
} from './components';
import { ThemedCard } from '@/components/custom/card';
import { WordlistSelectionModal } from '@/components/custom/wordlist';
import { useDefinitionGroups, useAnimationCycle, useProviders, useImageManagement } from './composables';
import { normalizeEtymology } from '@/utils/guards';

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

// Computed properties
const entry = computed(() => store.currentEntry);

// Force animation key update when word changes
watch(entry, (newEntry, oldEntry) => {
    if (newEntry?.word !== oldEntry?.word) {
        animationKey.value++;
    }
});

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

const handleImagesUpdated = async () => {
    // Refresh the current entry to get updated image data
    if (entry.value?.synth_entry_id) {
        await store.refreshSynthEntry(entry.value.synth_entry_id);
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