export interface SidebarDefinitionPreview {
    partOfSpeech: string;
    text: string;
    synonyms: string[];
}

export interface SidebarCluster {
    clusterId: string;
    clusterName: string;
    clusterDescription: string;
    partsOfSpeech: Array<{ type: string; count: number }>;
    maxRelevancy: number;
    definitions: SidebarDefinitionPreview[];
}

export interface SidebarSection {
    cluster: SidebarCluster;
    isActive: boolean;
    onClusterClick: () => void;
    onPartOfSpeechClick: (partOfSpeech: string) => void;
}