<template>
    <div v-if="entry" class="relative">
        <!-- Main Card -->
        <ThemedCard :variant="store.selectedCardVariant" class="relative">
            <!-- Theme Selector -->
            <ThemeSelector 
                v-model="store.selectedCardVariant"
                :isMounted="isMounted"
                :showDropdown="showThemeDropdown"
                @toggle-dropdown="showThemeDropdown = !showThemeDropdown"
            />
            
            <!-- First Image Display -->
            <EntryImage 
                :image="firstImage"
                :fallbackText="entry.word"
                @image-error="handleImageError"
                @image-click="handleImageClick"
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
                            >
                                <DefinitionItem
                                    v-for="(definition, defIndex) in cluster.definitions"
                                    :key="`${cluster.clusterId}-${defIndex}`"
                                    :definition="definition"
                                    :definitionIndex="getGlobalDefinitionIndex(clusterIndex, defIndex)"
                                    :isRegenerating="regeneratingIndex === getGlobalDefinitionIndex(clusterIndex, defIndex)"
                                    :isFirstInGroup="defIndex === 0"
                                    :isAISynthesized="!!entry.model_info"
                                    @regenerate="handleRegenerateExamples"
                                    @searchWord="store.searchWord"
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
    </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue';
import { useAppStore } from '@/stores';
import { CardContent } from '@/components/ui/card';
import {
    ThemeSelector,
    WordHeader,
    DefinitionCluster,
    DefinitionItem,
    ThesaurusView,
    Etymology,
    EntryImage
} from './components';
import { ThemedCard } from '@/components/custom/card';
import { useDefinitionGroups, useAnimationCycle, useProviders } from './composables';
import { normalizeEtymology } from '@/utils/guards';

// Store
const store = useAppStore();

// Reactive state
const regeneratingIndex = ref<number | null>(null);
const animationKey = ref(0);
const isMounted = ref(false);
const showThemeDropdown = ref(false);

// Computed properties
const entry = computed(() => store.currentEntry);

const normalizedEtymology = computed(() => {
    return normalizeEtymology(entry.value?.etymology);
});

const firstImage = computed(() => {
    let image = null;
    
    // First check synth entry images - prefer ones with descriptions
    if (entry.value?.images && entry.value.images.length > 0) {
        // Try to find an image with a description first
        image = entry.value.images.find(img => img.description) || entry.value.images[0];
    }
    
    // Then check definition images
    if (!image && entry.value?.definitions) {
        for (const def of entry.value.definitions) {
            if (def.images && def.images.length > 0) {
                // Try to find an image with a description first
                image = def.images.find(img => img.description) || def.images[0];
                break;
            }
        }
    }
    
    // If we have an image, construct the API URL
    if (image && image.id) {
        const imageWithUrl = {
            ...image,
            url: `/api/v1/images/${image.id}/content`
        };
        return imageWithUrl;
    }
    
    return image;
});

// Composables
const { groupedDefinitions } = useDefinitionGroups(entry);
const { startCycle, stopCycle } = useAnimationCycle(() => animationKey.value++);
const { usedProviders } = useProviders(entry);



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

const handleImageError = (event: Event) => {
    console.error('Failed to load image:', (event.target as HTMLImageElement).src);
    // Could hide the image or show a placeholder
    (event.target as HTMLImageElement).style.display = 'none';
};

const handleImageClick = () => {
    if (firstImage.value?.url) {
        // Open image in new tab
        window.open(firstImage.value.url, '_blank');
    }
};

// Keyboard navigation
const handleKeyDown = (event: KeyboardEvent) => {
    if (!entry.value?.definitions) return;
    
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        // Let ProgressiveSidebar handle the navigation
        document.dispatchEvent(new CustomEvent('navigate-definition', { 
            detail: { direction: event.key === 'ArrowDown' ? 'next' : 'prev' } 
        }));
    }
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
onMounted(() => {
    isMounted.value = true;
    startCycle();
    document.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
    stopCycle();
    document.removeEventListener('keydown', handleKeyDown);
});
</script>

<style scoped>
/* Mode switch transitions */
.mode-switch-enter-active {
    transition: all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1); /* ease-apple-bounce */
}

.mode-switch-leave-active {
    transition: all 0.2s ease-out;
}

.mode-switch-enter-from {
    opacity: 0;
    transform: scale(0.95) translateX(20px) rotate(1deg);
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
    transform: scale(0.95) translateX(-20px) rotate(-1deg);
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