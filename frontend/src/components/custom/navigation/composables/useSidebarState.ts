import { computed } from 'vue';
import { useStores } from '@/stores';
import { useDefinitionGroups } from '@/components/custom/definition/composables';
import { PART_OF_SPEECH_ORDER } from '@/components/custom/definition/constants';
import { normalizeEtymology } from '@/utils/guards';
import type { SidebarCluster } from '../types';
import type { SynthesizedDictionaryEntry } from '@/types';

export function useSidebarState() {
    const { searchResults, ui } = useStores();
    
    // Transform API entry to frontend format for compatibility
    const entry = computed(() => {
        const apiEntry = searchResults.currentEntry;
        if (!apiEntry) return null;
        // The API type is compatible with the frontend type for this composable
        return apiEntry as any as SynthesizedDictionaryEntry;
    });
    const { groupedDefinitions } = useDefinitionGroups(entry);
    
    // Transform grouped definitions to sidebar format
    const sidebarSections = computed((): SidebarCluster[] => {
        const sections: SidebarCluster[] = groupedDefinitions.value.map(group => {
            // Count parts of speech
            const partsOfSpeech = new Map<string, number>();
            
            group.definitions.forEach(def => {
                const pos = def.part_of_speech;
                partsOfSpeech.set(pos, (partsOfSpeech.get(pos) || 0) + 1);
            });
            
            // Convert to array and sort
            const sortedPOS = Array.from(partsOfSpeech.entries())
                .map(([type, count]) => ({ type, count }))
                .sort((a, b) => {
                    const aOrder = PART_OF_SPEECH_ORDER[a.type?.toLowerCase() as keyof typeof PART_OF_SPEECH_ORDER] || 999;
                    const bOrder = PART_OF_SPEECH_ORDER[b.type?.toLowerCase() as keyof typeof PART_OF_SPEECH_ORDER] || 999;
                    return aOrder - bOrder;
                });
            
            return {
                clusterId: group.clusterId,
                clusterDescription: group.clusterDescription,
                partsOfSpeech: sortedPOS,
                maxRelevancy: group.maxRelevancy
            };
        });
        
        // Add etymology section if available
        const normalizedEtymology = normalizeEtymology(entry.value?.etymology);
        if (normalizedEtymology?.text) {
            sections.push({
                clusterId: 'etymology',
                clusterDescription: 'Word origin and history',
                partsOfSpeech: [{ type: 'etymology', count: 1 }],
                maxRelevancy: 0.8
            });
        }
        
        return sections;
    });
    
    // Active states from UI store
    const activeCluster = computed({
        get: () => ui.sidebarActiveCluster,
        set: (value) => ui.setSidebarActiveCluster(value)
    });
    
    const activePartOfSpeech = computed({
        get: () => ui.sidebarActivePartOfSpeech,
        set: (value) => ui.setSidebarActivePartOfSpeech(value)
    });
    
    // Check if sidebar should be shown
    const shouldShowSidebar = computed(() => {
        return sidebarSections.value.length > 1;
    });
    
    return {
        sidebarSections,
        activeCluster,
        activePartOfSpeech,
        shouldShowSidebar,
        groupedDefinitions
    };
}