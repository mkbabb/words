import type { FlatSection } from '@mkbabb/glass-ui';
import type { GroupedDefinition } from '../types';

export interface FlatDefinitionCluster extends FlatSection {
    cluster: GroupedDefinition;
}

function estimateClusterHeight(cluster: GroupedDefinition): number {
    const headerHeight = 80; // cluster header + separator
    const defHeight = cluster.definitions.length * 180; // avg definition height
    return headerHeight + defHeight;
}

export function flattenDefinitionClusters(
    groups: GroupedDefinition[],
): FlatDefinitionCluster[] {
    return groups.map((cluster, index) => ({
        id: cluster.clusterId,
        index,
        depth: 0,
        parentId: null,
        rootId: cluster.clusterId,
        rootIndex: index,
        estimatedHeight: estimateClusterHeight(cluster),
        cluster,
    }));
}
