import { computed } from 'vue';
import { useStores } from '@/stores';
import { useDefinitionGroups } from '@/components/custom/definition/composables';
import { PART_OF_SPEECH_ORDER } from '@/components/custom/definition/constants';
import { normalizeEtymology } from '@/utils/guards';
import { useTreeIndex } from './useTreeIndex';
import type { SidebarCluster } from '../types';
import type { TreeNode } from './types';
import type { SynthesizedDictionaryEntry } from '@/types';

export function useSidebarState() {
    const { content } = useStores();

    // Transform API entry to frontend format, filtering by active provider tab
    const entry = computed(() => {
        const apiEntry = content.currentEntry;
        if (!apiEntry) return null;
        const raw = apiEntry as any as SynthesizedDictionaryEntry;

        const activeTab = content.activeSourceTab;
        // Synthesis view → show all definitions (current behaviour)
        if (!activeTab || activeTab === 'synthesis') {
            return raw;
        }

        // Provider view → filter to definitions whose providers_data includes this provider
        const filtered = (raw.definitions ?? []).filter((def: any) => {
            if (!def.providers_data) return false;
            const pdList = Array.isArray(def.providers_data)
                ? def.providers_data
                : [def.providers_data];
            return pdList.some((pd: any) => pd.provider === activeTab);
        });

        return { ...raw, definitions: filtered } as SynthesizedDictionaryEntry;
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
            
            // Build definition previews for hovercard
            const definitions = group.definitions.slice(0, 3).map(def => ({
                partOfSpeech: def.part_of_speech || '',
                text: def.text || def.definition || '',
                synonyms: (def.synonyms || []).slice(0, 4),
            }));

            return {
                clusterId: group.clusterId,
                clusterName: group.clusterName,
                clusterDescription: group.clusterDescription,
                partsOfSpeech: sortedPOS,
                maxRelevancy: group.maxRelevancy,
                definitions,
            };
        });
        
        // Add etymology section if available
        const normalizedEtymology = normalizeEtymology(entry.value?.etymology);
        if (normalizedEtymology?.text) {
            sections.push({
                clusterId: 'etymology',
                clusterName: 'Etymology',
                clusterDescription: 'Word origin and history',
                partsOfSpeech: [{ type: 'etymology', count: 1 }],
                maxRelevancy: 0.8,
                definitions: [],
            });
        }
        
        return sections;
    });
    
    // Active states from content store
    const activeCluster = computed({
        get: () => content.sidebarActiveCluster,
        set: (value) => content.setSidebarActiveCluster(value)
    });
    
    const activePartOfSpeech = computed({
        get: () => content.sidebarActivePartOfSpeech,
        set: (value) => content.setSidebarActivePartOfSpeech(value)
    });
    
    // Check if sidebar should be shown
    const shouldShowSidebar = computed(() => {
        return sidebarSections.value.length > 1;
    });

    // Build tree nodes from sidebar sections for scroll tracking
    const treeNodes = computed((): TreeNode[] => {
        return sidebarSections.value.map(section => ({
            id: section.clusterId,
            children: section.partsOfSpeech.map(pos => ({
                id: `${section.clusterId}-${pos.type}`,
            })),
        }));
    });

    // Build tree index (reactive — rebuilds when treeNodes change)
    const treeIndex = computed(() => {
        return useTreeIndex(treeNodes.value);
    });

    return {
        sidebarSections,
        activeCluster,
        activePartOfSpeech,
        shouldShowSidebar,
        groupedDefinitions,
        treeNodes,
        treeIndex,
    };
}