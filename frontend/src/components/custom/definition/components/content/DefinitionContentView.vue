<template>
    <!-- Mode Content -->
    <CardContent class="space-y-4 px-4 sm:px-6">
            <!-- Instant swap — no Transition wrapper (out-in doubles DOM for 200-350ms) -->
            <div
                :key="currentSubMode"
                class="space-y-4"
            >
                <!-- Dictionary Mode with Virtual Windowing -->
                <template
                    v-if="currentSubMode === 'dictionary'"
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
                        :style="clusterAnimReady ? { animationDelay: `${visIdx * STAGGER}ms` } : undefined"
                        :cluster="item.cluster"
                        :clusterIndex="item.index"
                        :totalClusters="totalClusters"
                        :cardVariant="cardVariant"
                        :editModeEnabled="editModeEnabled"
                        :isStreaming="isStreaming"
                        @update:cluster-name="(id: string, name: string) => $emit('update:cluster-name', id, name)"
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
                                regeneratingDefinitionIndex ===
                                getGlobalDefinitionIndex(
                                    item.index,
                                    defIndex
                                )
                            "
                            :isFirstInGroup="defIndex === 0"
                            :isAISynthesized="isAISynthesized"
                            :editModeEnabled="editModeEnabled"
                            :isStreaming="isStreaming"
                            :word="word"
                            @regenerate="$emit('regenerate', $event)"
                            @searchWord="$emit('search-word', $event)"
                            @addToWordlist="$emit('add-to-wordlist', $event)"
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
                    v-else-if="currentSubMode === 'thesaurus'"
                >
                    <ThesaurusView
                        :thesaurusData="thesaurusData"
                        :cardVariant="cardVariant"
                        :activeSource="activeSource"
                        @word-click="$emit('search-word', $event)"
                        @retry-thesaurus="$emit('retry-thesaurus')"
                        @switch-to-dictionary="$emit('switch-to-dictionary')"
                    />
                </template>

                <!-- AI Suggestions Mode -->
                <template
                    v-else-if="currentSubMode === 'suggestions'"
                >
                    <!-- This mode is handled by WordSuggestionDisplay in Home.vue -->
                    <div class="text-center text-muted-foreground">
                        Switching to suggestions mode...
                    </div>
                </template>
            </div>
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
        v-if="synonymChooser"
        :synonym-chooser="synonymChooser"
        @search-word="$emit('search-word', $event)"
    />

    <!-- Phrases & Idioms -->
    <PhrasesSection
        v-if="phrases?.length"
        :phrases="phrases"
    />

    <!-- Debug Info with Streaming Status -->
    <div v-if="entryId" class="mt-4 flex justify-center">
        <div
            class="flex items-center gap-2 rounded-md border border-border/30 bg-background/50 px-3 py-1 text-xs text-muted-foreground/50"
        >
            {{ entryId }}
            <div v-if="isStreaming" class="flex items-center gap-1">
                <div
                    class="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500"
                />
                <span class="text-blue-500">streaming</span>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch, provide } from 'vue';
import { EnsureTargetWindowKey } from '../../constants';
import { CardContent } from '@mkbabb/glass-ui';
import {
    DefinitionCluster,
    DefinitionItem,
    ThesaurusView,
    Etymology,
} from '../index';
import DefinitionStreamingSkeleton from '../../skeletons/DefinitionStreamingSkeleton.vue';
import SynonymChooserComponent from '../editing/SynonymChooser.vue';
import PhrasesSection from '../PhrasesSection.vue';
import {
    useDefinitionGroups,
    flattenDefinitionClusters,
    type FlatDefinitionCluster,
} from '../../composables';
import { useVirtualSectionWindow } from '@mkbabb/glass-ui';
import { normalizeEtymology } from '@/utils/guards';
import { STAGGER } from '@/utils/animations';
import type { CardVariant } from '@/types';

const props = defineProps<{
    entry: any;
    currentSubMode: string;
    cardVariant: CardVariant;
    editModeEnabled: boolean;
    isStreaming: boolean;
    activeSource: string;
    thesaurusData: any;
    regeneratingDefinitionIndex: number | null;
}>();

defineEmits<{
    'update:cluster-name': [clusterId: string, newName: string];
    'regenerate': [definitionIndex: number];
    'search-word': [word: string];
    'add-to-wordlist': [word: string];
    'retry-thesaurus': [];
    'switch-to-dictionary': [];
}>();

// Derived props
const word = computed(() => props.entry?.word);
const isAISynthesized = computed(() => !!props.entry?.model_info);
const entryId = computed(() => props.entry?.id);
const synonymChooser = computed(() => props.entry?.synonym_chooser);
const phrases = computed(() => props.entry?.phrases);

const normalizedEtymology = computed(() => {
    return normalizeEtymology(props.entry?.etymology);
});

// Smart skeleton logic
const expectedDefinitionCount = computed(() => {
    if (props.isStreaming) {
        const currentCount = props.entry?.definitions?.length || 0;
        const estimatedTotal = Math.max(3, currentCount + 1);
        return Math.min(estimatedTotal - currentCount, 3);
    }
    return 0;
});

const shouldShowDefinitionSkeletons = computed(() => {
    return props.isStreaming && expectedDefinitionCount.value > 0;
});

// Composables
const entryRef = computed(() => props.entry);
const { groupedDefinitions } = useDefinitionGroups(entryRef);

const totalClusters = computed(() => groupedDefinitions.value.length);

// Virtual windowing for definition clusters
const clusterContainerRef = ref<HTMLElement | null>(null);
const flatClusters = computed(() => flattenDefinitionClusters(groupedDefinitions.value));
// Cast to `any` to work around cross-package RefSymbol mismatch between
// the words frontend's Vue and glass-ui's Vue reactivity packages.
const {
    visibleItems,
    topSpacerPx,
    bottomSpacerPx,
    measureSection,
    ensureTargetWindow,
} = useVirtualSectionWindow({
    items: flatClusters as any,
    scrollContainer: ref(null) as any,
    contentEl: clusterContainerRef as any,
    overscanBeforePx: 400,
    overscanAfterPx: 800,
}) as unknown as {
    visibleItems: import('vue').ComputedRef<FlatDefinitionCluster[]>;
    topSpacerPx: import('vue').ComputedRef<number>;
    bottomSpacerPx: import('vue').ComputedRef<number>;
    measureSection: (id: string, el: HTMLElement | undefined) => void;
    ensureTargetWindow: (id: string) => void;
};

// Provide ensureTargetWindow for sidebar navigation (via provide/inject)
provide(EnsureTargetWindowKey, ensureTargetWindow);

// --- Staggered cluster entrance animation (CSS class toggle) ---
const clusterAnimReady = ref(false);

watch(
    () => props.entry?.word,
    (newWord: string | undefined, oldWord: string | undefined) => {
        if (newWord && oldWord && newWord !== oldWord) {
            clusterAnimReady.value = true;
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
/* Staggered cluster entrance on word change */
@keyframes clusterSlideIn {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}
.animate-cluster-in {
    animation: clusterSlideIn 0.3s ease both;
}
</style>
