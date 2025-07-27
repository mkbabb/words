<template>
    <div 
        class="themed-card themed-shadow-lg rounded-lg bg-background/95 p-2 backdrop-blur-sm"
        :data-theme="selectedCardVariant || 'default'"
    >
        <!-- Navigation Sections -->
        <nav class="scrollbar-thin max-h-[calc(100vh-8rem)] space-y-0.5 overflow-y-auto overflow-x-hidden">
            <template v-for="(cluster, index) in sidebarSections" :key="cluster.clusterId">
                <SidebarCluster
                    :cluster="cluster"
                    :isActive="activeCluster === cluster.clusterId"
                    :activePartOfSpeech="activePartOfSpeech"
                    :cardVariant="selectedCardVariant"
                    @cluster-click="handleClusterClick(cluster.clusterId)"
                    @part-of-speech-click="(pos) => handlePartOfSpeechClick(cluster.clusterId, pos)"
                />
                
                <!-- Separator -->
                <hr
                    v-if="index < sidebarSections.length - 1"
                    class="my-2 border-0 h-px bg-gradient-to-r from-transparent via-muted-foreground/20 to-transparent dark:via-muted-foreground/30"
                />
            </template>
        </nav>
    </div>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { useAppStore } from '@/stores';
import { useSidebarState, useSidebarNavigation, useActiveTracking } from './composables';
import SidebarCluster from './components/SidebarCluster.vue';

const store = useAppStore();
const { selectedCardVariant } = storeToRefs(store);

// Use composables
const { 
    sidebarSections, 
    activeCluster, 
    activePartOfSpeech 
} = useSidebarState();

const { 
    scrollToCluster, 
    scrollToPartOfSpeech 
} = useSidebarNavigation();

// Set up active tracking
useActiveTracking({
    activeCluster,
    activePartOfSpeech,
    sidebarSections
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
/* Scrollbar styling */
.scrollbar-thin {
    scrollbar-width: thin;
    scrollbar-color: hsl(var(--border) / 0.3) transparent;
}

.scrollbar-thin::-webkit-scrollbar {
    width: 4px;
}

.scrollbar-thin::-webkit-scrollbar-track {
    background: transparent;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
    background: hsl(var(--border) / 0.3);
    border-radius: 2px;
}

.scrollbar-thin::-webkit-scrollbar-thumb:hover {
    background: hsl(var(--primary) / 0.5);
}


/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
    * {
        transition-duration: 0.01ms !important;
        animation-duration: 0.01ms !important;
    }
}
</style>