<template>
    <div v-if="entry" class="relative flex gap-4">
        <!-- Progressive Sidebar -->
        <ProgressiveSidebar 
            v-if="shouldShowSidebar" 
            :groupedDefinitions="groupedDefinitions"
            class="hidden w-48 flex-shrink-0 xl:block sticky top-4 self-start"
            style="z-index: 40;"
        />

        <!-- Main Card -->
        <ThemedCard :variant="store.selectedCardVariant" class="relative flex-1">
            <!-- Theme Selector -->
            <ThemeSelector 
                v-model="store.selectedCardVariant"
                :isMounted="isMounted"
                :showDropdown="showThemeDropdown"
                @toggle-dropdown="showThemeDropdown = !showThemeDropdown"
            />

            <!-- Header -->
            <WordHeader 
                :word="entry.word"
                :pronunciation="entry.pronunciation"
                :pronunciationMode="store.pronunciationMode"
                :providers="usedProviders"
                :animationType="'typewriter'"
                :animationKey="animationKey"
                @toggle-pronunciation="store.togglePronunciation"
            />

            <div class="themed-hr h-px mb-4" />

            <!-- Mode Content -->
            <Transition
                mode="out-in"
                enter-active-class="transition-all duration-300 ease-apple-bounce"
                leave-active-class="transition-all duration-200 ease-out"
                enter-from-class="opacity-0 scale-95 translate-x-8 rotate-1"
                enter-to-class="opacity-100 scale-100 translate-x-0 rotate-0"
                leave-from-class="opacity-100 scale-100 translate-x-0 rotate-0"
                leave-to-class="opacity-0 scale-95 -translate-x-8 -rotate-1"
            >
                <CardContent :key="store.mode" class="space-y-4">
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
                                @regenerate="handleRegenerateExamples"
                                @searchWord="store.searchWord"
                            />
                        </DefinitionCluster>
                    </template>

                    <!-- Thesaurus Mode -->
                    <ThesaurusView
                        v-else-if="store.mode === 'thesaurus'"
                        :thesaurusData="store.currentThesaurus"
                        :cardVariant="store.selectedCardVariant"
                        @word-click="store.searchWord"
                    />
                </CardContent>
            </Transition>

            <!-- Etymology -->
            <Etymology v-if="entry.etymology" :etymology="entry.etymology" />
        </ThemedCard>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue';
import { useAppStore } from '@/stores';
import { CardContent } from '@/components/ui/card';
import {
    ThemeSelector,
    WordHeader,
    DefinitionCluster,
    DefinitionItem,
    ThesaurusView,
    Etymology
} from './components';
import { ThemedCard } from '@/components/custom/card';
import { ProgressiveSidebar } from '@/components/custom/navigation';
import { useDefinitionGroups, useAnimationCycle, useProviders } from './composables';
import type { TransformedDefinition } from '@/types';

// Store
const store = useAppStore();

// Reactive state
const regeneratingIndex = ref<number | null>(null);
const animationKey = ref(0);
const isMounted = ref(false);
const showThemeDropdown = ref(false);

// Computed properties
const entry = computed(() => store.currentEntry);

// Composables
const { groupedDefinitions } = useDefinitionGroups(entry);
const { startCycle, stopCycle } = useAnimationCycle(() => animationKey.value++);
const { usedProviders } = useProviders(entry);

// Sidebar visibility
const shouldShowSidebar = computed(() => {
    if (!entry.value?.definitions) return false;
    const clusters = new Set();
    entry.value.definitions.forEach((def: TransformedDefinition) => {
        clusters.add(def.meaning_cluster?.id || 'default');
    });
    return clusters.size > 1;
});


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