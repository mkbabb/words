export interface SidebarCluster {
    clusterId: string;
    clusterDescription: string;
    partsOfSpeech: Array<{ type: string; count: number }>;
    maxRelevancy: number;
}

export interface SidebarSection {
    cluster: SidebarCluster;
    isActive: boolean;
    onClusterClick: () => void;
    onPartOfSpeechClick: (partOfSpeech: string) => void;
}