<template>
    <HoverCardContent
        :class="cn(
            'themed-hovercard z-[80] w-96',
            variant !== 'default' ? 'themed-shadow-sm' : ''
        )"
        :data-theme="variant || 'default'"
        :side="side"
        :align="align"
    >
        <div class="space-y-4">
            <div>
                <h4 class="mb-2 text-base font-semibold uppercase">
                    {{ formatClusterLabel(cluster.clusterId) }}
                </h4>
                <p class="mb-4 text-sm text-muted-foreground">
                    {{ cluster.clusterDescription }}
                </p>
                <div class="space-y-2">
                    <div class="flex items-center justify-between border-b border-border/30 py-1.5">
                        <span class="text-sm text-muted-foreground">Cluster ID</span>
                        <span class="font-mono text-sm">{{ cluster.clusterId }}</span>
                    </div>
                    <div class="flex items-center justify-between border-b border-border/30 py-1.5">
                        <span class="text-sm text-muted-foreground">Relevance Score</span>
                        <span class="text-sm font-medium">
                            {{ Math.round((cluster.maxRelevancy || 1.0) * 100) }}%
                        </span>
                    </div>
                    <div class="flex items-center justify-between border-b border-border/30 py-1.5">
                        <span class="text-sm text-muted-foreground">Parts of Speech</span>
                        <span class="text-sm font-medium">{{ cluster.partsOfSpeech.length }}</span>
                    </div>
                    <div class="flex items-center justify-between py-1.5">
                        <span class="text-sm text-muted-foreground">Total Definitions</span>
                        <span class="text-sm font-medium">{{ totalDefinitions }}</span>
                    </div>
                </div>
            </div>
        </div>
    </HoverCardContent>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { HoverCardContent } from '@/components/ui';
import { cn } from '@/utils';
import { formatClusterLabel } from '@/components/custom/definition/utils';
import type { SidebarCluster } from '../types';

interface Props {
    cluster: SidebarCluster;
    variant?: string;
    side?: 'top' | 'right' | 'bottom' | 'left';
    align?: 'start' | 'center' | 'end';
}

const props = defineProps<Props>();

const totalDefinitions = computed(() => {
    return props.cluster.partsOfSpeech.reduce((sum, pos) => sum + pos.count, 0);
});
</script>