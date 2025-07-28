<template>
    <div 
        class="themed-card themed-shadow-lg rounded-lg bg-background/95 p-2 backdrop-blur-sm"
        :data-theme="selectedCardVariant || 'default'"
    >
        <!-- Navigation Sections -->
        <nav ref="navContainer" class="scrollbar-thin max-h-[calc(100vh-8rem)] space-y-0 overflow-y-auto overflow-x-hidden">
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
                        :activePartOfSpeech="activePartOfSpeech"
                        :cardVariant="selectedCardVariant"
                        @cluster-click="handleClusterClick(cluster.clusterId)"
                        @part-of-speech-click="(pos) => handlePartOfSpeechClick(cluster.clusterId, pos)"
                    />
                    
                    <!-- Regular separator between non-etymology clusters -->
                    <hr
                        v-if="index < sidebarSections.length - 1 && sidebarSections[index + 1].clusterId !== 'etymology'"
                        class="my-1 border-0 h-px bg-gradient-to-r from-transparent via-muted-foreground/20 to-transparent dark:via-muted-foreground/30"
                    />
                </template>
            </template>
        </nav>
    </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { storeToRefs } from 'pinia';
import { useAppStore } from '@/stores';
import { useSidebarState, useSidebarNavigation, useActiveTracking } from './composables';
import SidebarCluster from './components/SidebarCluster.vue';

const store = useAppStore();
const { selectedCardVariant } = storeToRefs(store);

// Template refs
const navContainer = ref<HTMLElement>();

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

// Auto-scroll sidebar to keep active elements visible
const scrollSidebarToElement = async (selector: string) => {
    await nextTick();
    
    if (!navContainer.value) return;
    
    const element = navContainer.value.querySelector(selector) as HTMLElement;
    if (!element) return;
    
    const containerRect = navContainer.value.getBoundingClientRect();
    const elementRect = element.getBoundingClientRect();
    
    // Check if element is already fully visible
    const isVisible = (
        elementRect.top >= containerRect.top &&
        elementRect.bottom <= containerRect.bottom
    );
    
    if (!isVisible) {
        // Calculate scroll position to center the element
        const elementTop = element.offsetTop;
        const containerHeight = navContainer.value.clientHeight;
        const elementHeight = element.clientHeight;
        
        // Center the element in the container
        const scrollTop = elementTop - (containerHeight / 2) + (elementHeight / 2);
        
        navContainer.value.scrollTo({
            top: Math.max(0, scrollTop),
            behavior: 'smooth'
        });
    }
};

// Watch for active changes and auto-scroll sidebar
watch([activeCluster, activePartOfSpeech], async ([newCluster, newPOS]) => {
    if (newPOS) {
        // Scroll to the active part of speech button
        await scrollSidebarToElement(`[data-sidebar-pos="${newPOS}"]`);
    } else if (newCluster) {
        // Scroll to the active cluster
        await scrollSidebarToElement(`[data-sidebar-cluster="${newCluster}"]`);
    }
});

// Handlers
const handleClusterClick = async (clusterId: string) => {
    scrollToCluster(clusterId);
    // Ensure clicked element is visible in sidebar
    await scrollSidebarToElement(`[data-sidebar-cluster="${clusterId}"]`);
};

const handlePartOfSpeechClick = async (clusterId: string, partOfSpeech: string) => {
    scrollToPartOfSpeech(clusterId, partOfSpeech);
    // Ensure clicked element is visible in sidebar
    const posId = `${clusterId}-${partOfSpeech}`;
    await scrollSidebarToElement(`[data-sidebar-pos="${posId}"]`);
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