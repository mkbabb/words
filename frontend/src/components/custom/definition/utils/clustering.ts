import type { Definition, TransformedDefinition } from '@/types';
import type { GroupedDefinition } from '../types';
import { PART_OF_SPEECH_ORDER } from '../constants';

/**
 * Groups definitions by their meaning cluster
 */
export function groupDefinitionsByCluster(definitions: Definition[]): GroupedDefinition[] {
    if (!definitions || definitions.length === 0) return [];

    // Group definitions by meaning cluster
    const clusters = new Map<string, GroupedDefinition>();

    definitions.forEach((definition) => {
        const clusterId = definition.meaning_cluster?.id || 'default';
        const clusterDescription = definition.meaning_cluster?.description || 'General';

        if (!clusters.has(clusterId)) {
            clusters.set(clusterId, {
                clusterId,
                clusterDescription,
                definitions: [],
                maxRelevancy: definition.relevancy || 1.0,
            });
        }

        const cluster = clusters.get(clusterId)!;
        // Cast definition since API transforms it
        const transformedDef = definition as any as TransformedDefinition;
        cluster.definitions.push(transformedDef);

        // Track highest relevancy in cluster for sorting
        if ((definition.relevancy || 1.0) > cluster.maxRelevancy) {
            cluster.maxRelevancy = definition.relevancy || 1.0;
        }
    });

    // Sort clusters by maximum relevancy (highest first)
    const sortedClusters = Array.from(clusters.values()).sort(
        (a, b) => b.maxRelevancy - a.maxRelevancy
    );

    // Sort definitions within each cluster
    sortedClusters.forEach((cluster) => {
        cluster.definitions = sortDefinitions(cluster.definitions);
    });

    return sortedClusters;
}

/**
 * Sorts definitions by part of speech and relevancy
 */
export function sortDefinitions(definitions: TransformedDefinition[]): TransformedDefinition[] {
    return definitions.sort((a, b) => {
        // First, sort by word type (nouns first, verbs second, etc.)
        const aTypeOrder =
            PART_OF_SPEECH_ORDER[
                a.part_of_speech?.toLowerCase() as keyof typeof PART_OF_SPEECH_ORDER
            ] || 999;
        const bTypeOrder =
            PART_OF_SPEECH_ORDER[
                b.part_of_speech?.toLowerCase() as keyof typeof PART_OF_SPEECH_ORDER
            ] || 999;

        if (aTypeOrder !== bTypeOrder) {
            return aTypeOrder - bTypeOrder;
        }

        // Then sort by relevancy within the same word type (highest first)
        return (b.relevancy || 1.0) - (a.relevancy || 1.0);
    });
}

/**
 * Formats cluster ID for display
 * e.g., "example_representative" -> "Representative"
 */
export function formatClusterLabel(clusterId: string): string {
    // Remove word prefix and get the cluster name part
    const parts = clusterId.split('_');
    if (parts.length > 1) {
        // Get the cluster name part(s) after the word
        const clusterName = parts.slice(1).join(' ');
        // Capitalize first letter
        return clusterName.charAt(0).toUpperCase() + clusterName.slice(1);
    }
    // Fallback for non-standard formats
    return clusterId.charAt(0).toUpperCase() + clusterId.slice(1);
}