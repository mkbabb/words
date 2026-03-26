<template>
    <div :id="cluster.clusterId" :data-cluster-id="cluster.clusterId" class="space-y-1 text-2xl">
        <!-- Cluster header with gradient divider -->
        <div
            v-if="totalClusters > 1"
            :class="clusterIndex === 0 ? 'pb-3' : 'mt-0 pb-3'"
        >
            <!-- Separator between clusters (not before first) -->
            <hr v-if="clusterIndex > 0" class="my-4 border-border/50" />
            <HoverCard :open-delay="300" :close-delay="100">
                <HoverCardTrigger as-child>
                    <EditableField
                        :model-value="cluster.clusterName"
                        field-name="cluster name"
                        :edit-mode="props.editModeEnabled"
                        @update:model-value="
                            (val) =>
                                emit(
                                    'update:cluster-name',
                                    cluster.clusterId,
                                    String(val)
                                )
                        "
                    >
                        <template #display>
                            <h4
                                class="inline-block cursor-help rounded-lg border border-border/50 bg-muted/30 px-3 py-1.5 text-sm font-semibold tracking-wide uppercase transition-fast hover:border-border hover:bg-muted/50"
                            >
                                {{ cluster.clusterName }}
                            </h4>
                        </template>
                    </EditableField>
                </HoverCardTrigger>
                <HoverCardContent
                    :class="
                        cn(
                            'themed-hovercard z-hovercard w-96',
                            cardVariant !== 'default' ? 'shadow-cartoon-sm' : ''
                        )
                    "
                    :data-theme="cardVariant || 'default'"
                    side="top"
                    align="start"
                >
                    <div class="space-y-4">
                        <div>
                            <h4 class="mb-2 text-base font-semibold">
                                {{ cluster.clusterName }}
                            </h4>
                            <p class="mb-4 text-sm text-muted-foreground">
                                {{ cluster.clusterDescription }}
                            </p>
                            <div class="space-y-2">
                                <div
                                    class="flex items-center justify-between border-b border-border/30 py-1.5"
                                >
                                    <span class="text-sm text-muted-foreground"
                                        >Cluster ID</span
                                    >
                                    <span class="font-mono text-sm">{{
                                        cluster.clusterId
                                    }}</span>
                                </div>
                                <div
                                    class="flex items-center justify-between border-b border-border/30 py-1.5"
                                >
                                    <span class="text-sm text-muted-foreground"
                                        >Relevance Score</span
                                    >
                                    <span class="text-sm font-medium"
                                        >{{
                                            Math.round(
                                                (cluster.maxRelevancy || 1.0) *
                                                    100
                                            )
                                        }}%</span
                                    >
                                </div>
                                <div
                                    class="flex items-center justify-between border-b border-border/30 py-1.5"
                                >
                                    <span class="text-sm text-muted-foreground"
                                        >Total Definitions</span
                                    >
                                    <span class="text-sm font-medium">{{
                                        cluster.definitions.length
                                    }}</span>
                                </div>
                                <div
                                    v-if="
                                        cluster.definitions[0]?.meaning_cluster
                                            ?.relevance
                                    "
                                    class="flex items-center justify-between py-1.5"
                                >
                                    <span class="text-sm text-muted-foreground"
                                        >Confidence</span
                                    >
                                    <span class="text-sm font-medium"
                                        >{{
                                            Math.round(
                                                cluster.definitions[0]
                                                    .meaning_cluster.relevance *
                                                    100
                                            )
                                        }}%</span
                                    >
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
import {
    HoverCard,
    HoverCardContent,
    HoverCardTrigger,
} from '@/components/ui/hover-card';
import { cn } from '@/utils';
import type { GroupedDefinition } from '../../types';
import type { CardVariant } from '@/types';
import EditableField from '../editing/EditableField.vue';

interface DefinitionClusterProps {
    cluster: GroupedDefinition;
    clusterIndex: number;
    totalClusters: number;
    cardVariant: CardVariant;
    editModeEnabled?: boolean;
}

const props = defineProps<DefinitionClusterProps>();

const emit = defineEmits<{
    'update:cluster-name': [clusterId: string, newName: string];
}>();
</script>
