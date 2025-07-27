<template>
    <div
        :data-cluster-id="cluster.clusterId"
        class="text-2xl space-y-1"
    >
        <!-- Separator between clusters (not before first) -->
        <hr
            v-if="clusterIndex > 0 && totalClusters > 1"
            class="my-6 border-0 h-px bg-gradient-to-r from-transparent via-muted-foreground/20 to-transparent dark:via-muted-foreground/30"
        />
        
        <!-- Cluster header with gradient divider -->
        <div
            v-if="totalClusters > 1"
            :class="clusterIndex === 0 ? 'pb-3' : 'mt-0 pb-3'"
        >
            <HoverCard :open-delay="600" :close-delay="100">
                <HoverCardTrigger as-child>
                    <h4
                        class="text-sm font-semibold tracking-wide uppercase inline-block px-3 py-1.5 rounded-md bg-muted/30 border border-border/50 hover:bg-muted/50 hover:border-border transition-all duration-200 cursor-help"
                    >
                        {{ formatClusterLabel(cluster.clusterId) }}
                    </h4>
                </HoverCardTrigger>
                <HoverCardContent 
                    :class="cn(
                        'themed-hovercard w-96 z-[80]',
                        cardVariant !== 'default' ? 'themed-shadow-sm' : ''
                    )"
                    :data-theme="cardVariant || 'default'"
                    side="top"
                    align="start"
                >
                    <div class="space-y-4">
                        <div>
                            <h4 class="text-base font-semibold mb-2">{{ formatClusterLabel(cluster.clusterId) }}</h4>
                            <p class="text-sm text-muted-foreground mb-4">{{ cluster.clusterDescription }}</p>
                            <div class="space-y-2">
                                <div class="flex justify-between items-center py-1.5 border-b border-border/30">
                                    <span class="text-sm text-muted-foreground">Cluster ID</span>
                                    <span class="text-sm font-mono">{{ cluster.clusterId }}</span>
                                </div>
                                <div class="flex justify-between items-center py-1.5 border-b border-border/30">
                                    <span class="text-sm text-muted-foreground">Relevance Score</span>
                                    <span class="text-sm font-medium">{{ Math.round((cluster.maxRelevancy || 1.0) * 100) }}%</span>
                                </div>
                                <div class="flex justify-between items-center py-1.5 border-b border-border/30">
                                    <span class="text-sm text-muted-foreground">Total Definitions</span>
                                    <span class="text-sm font-medium">{{ cluster.definitions.length }}</span>
                                </div>
                                <div v-if="cluster.definitions[0]?.meaning_cluster?.relevance" 
                                     class="flex justify-between items-center py-1.5">
                                    <span class="text-sm text-muted-foreground">Confidence</span>
                                    <span class="text-sm font-medium">{{ Math.round(cluster.definitions[0].meaning_cluster.relevance * 100) }}%</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </HoverCardContent>
            </HoverCard>
        </div>

        <!-- Definitions slot -->
        <slot />
    </div>
</template>

<script setup lang="ts">
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import { cn } from '@/utils';
import { formatClusterLabel } from '../utils/clustering';
import type { GroupedDefinition } from '../types';
import type { CardVariant } from '@/types';

interface DefinitionClusterProps {
    cluster: GroupedDefinition;
    clusterIndex: number;
    totalClusters: number;
    cardVariant: CardVariant;
}

defineProps<DefinitionClusterProps>();
</script>