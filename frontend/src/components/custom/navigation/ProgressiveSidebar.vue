<template>
    <div
        class="themed-card shadow-cartoon-lg rounded-lg bg-background/95 p-2 backdrop-blur-sm"
        :data-theme="selectedCardVariant || 'default'"
    >
        <!-- Navigation Sections -->
        <nav ref="navContainer" class="scrollbar-thin max-h-[calc(100dvh-8rem)] space-y-0 overflow-y-auto">
            <TransitionGroup name="sidebar-item" tag="div" class="space-y-0">
            <template v-for="(cluster, index) in sidebarSections" :key="cluster.clusterId">
                <!-- Special handling for etymology -->
                <template v-if="cluster.clusterId === 'etymology'">
                    <!-- Different separator style before etymology -->
                    <hr
                        v-if="index > 0"
                        class="my-1.5 border-0 h-0.5 bg-border/50"
                    />
                    <button
                        @click="handleClusterClick('etymology')"
                        data-toc-id="etymology"
                        data-sidebar-cluster="etymology"
                        :class="[
                            'w-full text-left px-3 py-2 rounded-md transition-all duration-200',
                            activeCluster === 'etymology'
                                ? 'bg-primary/10 text-primary'
                                : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground'
                        ]"
                    >
                        <h4 class="text-sm font-semibold">Etymology</h4>
                    </button>
                </template>

                <!-- Regular clusters -->
                <template v-else>
                    <SidebarCluster
                        :cluster="cluster"
                        :isActive="activeCluster === cluster.clusterId"
                        :activePartOfSpeech="activePartOfSpeech || ''"
                        :cardVariant="selectedCardVariant"
                        @cluster-click="handleClusterClick(cluster.clusterId)"
                        @part-of-speech-click="(pos) => handlePartOfSpeechClick(cluster.clusterId, pos)"
                    />

                    <!-- Regular separator between non-etymology clusters -->
                    <hr
                        v-if="index < sidebarSections.length - 1 && sidebarSections[index + 1].clusterId !== 'etymology'"
                        class="my-1 border-0 h-px divider-h"
                    />
                </template>
            </template>
            </TransitionGroup>
        </nav>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, inject } from 'vue';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { useStores } from '@/stores';
import { useSidebarState, useSidebarNavigation, useScrollTracker, useSidebarFollow } from './composables';
import SidebarCluster from './components/SidebarCluster.vue';

const lookupMode = useLookupMode();
const { content } = useStores();
const selectedCardVariant = computed(() => lookupMode.selectedCardVariant);

// Template refs
const navContainer = ref<HTMLElement | null>(null);

// Inject ensureTargetWindow from DefinitionDisplay (provided via provide/inject)
const ensureTargetWindow = inject<((id: string) => void) | null>('ensureTargetWindow', null);

// Use composables
const {
    sidebarSections,
    activeCluster,
    activePartOfSpeech,
    treeNodes,
    treeIndex,
} = useSidebarState();

const {
    scrollToCluster,
    scrollToPartOfSpeech,
} = useSidebarNavigation({
    ensureTargetWindow: ensureTargetWindow ?? undefined,
});

// Set up tree-based scroll tracking (reactive — re-initializes on tree change)
const { activeId, activeRootId } = useScrollTracker(
    () => treeNodes.value,
    () => treeIndex.value.index,
    { sidebarEl: navContainer },
);

// Set up damped sidebar follow
useSidebarFollow({
    sidebarEl: navContainer,
    activeId,
    activeRootId,
});

// Sync scroll tracker's activeId back to content store
watch(activeId, (id) => {
    if (!id) return;

    const entry = treeIndex.value.index.get(id);
    if (!entry) return;

    if (entry.depth === 0) {
        content.setSidebarActiveCluster(id);
        content.setSidebarActivePartOfSpeech(null);
    } else {
        content.setSidebarActiveCluster(entry.parentId);
        content.setSidebarActivePartOfSpeech(id);
    }
});

// Handlers
const handleClusterClick = (clusterId: string) => {
    scrollToCluster(clusterId);
};

const handlePartOfSpeechClick = (clusterId: string, partOfSpeech: string) => {
    scrollToPartOfSpeech(clusterId, partOfSpeech);
};
</script>

<style scoped>
.sidebar-item-enter-active {
    transition: opacity 0.25s ease, transform 0.25s ease;
}
.sidebar-item-leave-active {
    transition: opacity 0.15s ease, transform 0.15s ease;
}
.sidebar-item-enter-from {
    opacity: 0;
    transform: translateX(-8px);
}
.sidebar-item-leave-to {
    opacity: 0;
    transform: translateX(-8px);
}
.sidebar-item-move {
    transition: transform 0.25s ease;
}
</style>
