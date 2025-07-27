import { computed, type ComputedRef } from 'vue';
import type { TransformedDefinition, SynthesizedDictionaryEntry } from '@/types';
import type { GroupedDefinition } from '../types';

export function useDefinitionGroups(entry: ComputedRef<SynthesizedDictionaryEntry | null>) {
    const groupedDefinitions = computed<GroupedDefinition[]>(() => {
        if (!entry.value?.definitions) return [];

        const groups = new Map<string, TransformedDefinition[]>();
        
        entry.value.definitions.forEach((def: TransformedDefinition) => {
            const clusterId = def.meaning_cluster?.id || 'default';
            if (!groups.has(clusterId)) {
                groups.set(clusterId, []);
            }
            groups.get(clusterId)!.push(def);
        });

        return Array.from(groups.entries()).map(([clusterId, definitions]) => {
            // Calculate max relevancy from all definitions in cluster
            const maxRelevancy = Math.max(
                ...definitions.map(d => d.meaning_cluster?.relevance || 0),
                0
            );
            
            return {
                clusterId,
                definitions,
                clusterDescription: definitions[0]?.meaning_cluster?.name || 'General meaning',
                maxRelevancy
            };
        });
    });

    return {
        groupedDefinitions
    };
}