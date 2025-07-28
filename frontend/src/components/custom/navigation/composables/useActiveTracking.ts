import { onMounted, watch, type Ref } from 'vue';
import { useScrollTracking } from './useScrollTracking';
import type { SidebarCluster } from '../types';

interface UseActiveTrackingOptions {
    activeCluster: Ref<string>;
    activePartOfSpeech: Ref<string>;
    sidebarSections: Ref<SidebarCluster[]>;
}

export function useActiveTracking({
    activeCluster,
    activePartOfSpeech,
    sidebarSections
}: UseActiveTrackingOptions) {
    // Create active state map for multi-level tracking
    const activeStates = new Map([
        [0, activeCluster], // Level 0: clusters
        [1, activePartOfSpeech] // Level 1: parts of speech
    ]);
    
    const { trackElement, setupObserver } = useScrollTracking({
        activeStates,
        rootMargin: '-20% 0px -20% 0px',
        threshold: [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1],
        scrollDirectionBuffer: 30
    });
    
    // Register all elements for tracking
    const registerElements = () => {
        // Track clusters
        sidebarSections.value.forEach(cluster => {
            const clusterElement = document.querySelector(`[data-cluster-id="${cluster.clusterId}"]`);
            if (clusterElement) {
                trackElement(clusterElement, cluster.clusterId, 0);
            }
            
            // Track parts of speech within each cluster
            cluster.partsOfSpeech.forEach(pos => {
                const posId = `${cluster.clusterId}-${pos.type}`;
                const posElements = document.querySelectorAll(`[data-part-of-speech="${posId}"]`);
                
                posElements.forEach((element) => {
                    // Track all elements but use the same ID for all instances of a part of speech
                    // This way, if any instance is visible, the part of speech is considered active
                    trackElement(element, posId, 1, cluster.clusterId);
                });
            });
        });
    };
    
    // Initialize on mount
    onMounted(() => {
        if (sidebarSections.value.length > 0) {
            registerElements();
            
            // Set initial state if not already set
            if (!activeCluster.value && sidebarSections.value.length > 0) {
                const firstCluster = sidebarSections.value[0];
                activeCluster.value = firstCluster.clusterId;
                
                if (firstCluster.partsOfSpeech.length > 0) {
                    activePartOfSpeech.value = `${firstCluster.clusterId}-${firstCluster.partsOfSpeech[0].type}`;
                }
            }
        }
    });
    
    // Re-register when sections change
    watch(() => sidebarSections.value, () => {
        if (sidebarSections.value.length > 0) {
            // Re-setup observer to track new elements
            setupObserver();
            registerElements();
        }
    }, { deep: true });
    
    return {
        registerElements
    };
}