<template>
    <div
        class="themed-card overflow-visible shadow-cartoon-lg bg-background/92 p-2 rounded-xl"
        :data-theme="selectedCardVariant || 'default'"
    >
        <!-- Navigation Sections -->
        <nav ref="navContainer" class="scrollbar-thin max-h-[calc(100dvh-8rem)] space-y-0 overflow-y-auto">
            <TransitionGroup name="sidebar-item" tag="div" class="space-y-0.5">
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
                            'w-full text-left px-3 py-2 rounded-md transition-fast',
                            activeCluster === 'etymology'
                                ? 'bg-primary/10 text-primary'
                                : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground'
                        ]"
                    >
                        <h4 class="text-sm font-medium">Etymology</h4>
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
import { useSidebarState, useSidebarNavigation } from './composables';
import { useScrollTracker, useSidebarFollow } from '@mkbabb/glass-ui';
import SidebarCluster from './components/SidebarCluster.vue';
import { EnsureTargetWindowKey } from '@/components/custom/definition/constants';

const lookupMode = useLookupMode();
const { content } = useStores();
const selectedCardVariant = computed(() => lookupMode.selectedCardVariant);

// Template refs
const navContainer = ref<HTMLElement | null>(null);

// Inject ensureTargetWindow from DefinitionContentView (provided via typed InjectionKey)
const ensureTargetWindow = inject(EnsureTargetWindowKey, undefined);

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
    ensureTargetWindow,
});

// Set up tree-based scroll tracking (reactive — re-initializes on tree change)
const { activeId, activeRootId } = useScrollTracker(
    () => treeNodes.value,
    () => treeIndex.value.index,
);

// Set up damped sidebar follow
// Cast navContainer to satisfy glass-ui's Ref type (cross-package RefSymbol mismatch).
useSidebarFollow({
    sidebarEl: navContainer as any,
    activeId,
    activeRootId,
});

// Sync scroll tracker's activeId back to content store.
// Use a getter to unwrap the glass-ui Ref (avoids cross-package RefSymbol mismatch).
watch(() => activeId.value, (id) => {
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
