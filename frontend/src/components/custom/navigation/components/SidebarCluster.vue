<template>
    <div class="space-y-0">
        <!-- Cluster Header -->
        <HoverCard :open-delay="600" :close-delay="100">
            <HoverCardTrigger as-child>
                <button
                    @click="$emit('cluster-click')"
                    :data-sidebar-cluster="cluster.clusterId"
                    :class="[
                        'group flex w-full items-center rounded-md px-2 py-1 text-left text-sm transition-all duration-200',
                        isActive
                            ? 'font-bold text-foreground'
                            : 'font-normal text-foreground/80 hover:bg-muted/30 hover:text-foreground'
                    ]"
                >
                    <div class="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap pr-2">
                        <ShimmerText
                            v-if="isActive"
                            :text="formatClusterLabel(cluster.clusterId).toUpperCase()"
                            text-class="themed-cluster-title text-left text-xs font-bold uppercase tracking-wider"
                            :duration="400"
                            :interval="15000"
                        />
                        <span
                            v-else
                            class="themed-cluster-title text-left text-xs font-bold uppercase tracking-wider"
                        >
                            {{ formatClusterLabel(cluster.clusterId).toUpperCase() }}
                        </span>
                    </div>
                    <div
                        v-if="isActive"
                        class="ml-2 h-2 w-2 flex-shrink-0 rounded-full bg-primary/30 transition-all duration-300"
                    />
                </button>
            </HoverCardTrigger>
            <SidebarHoverCard
                :cluster="cluster"
                :variant="cardVariant"
                side="right"
                align="start"
            />
        </HoverCard>

        <!-- Parts of Speech -->
        <div class="ml-2 space-y-0">
            <SidebarPartOfSpeech
                v-for="partOfSpeech in cluster.partsOfSpeech"
                :key="`${cluster.clusterId}-${partOfSpeech.type}`"
                :clusterId="cluster.clusterId"
                :partOfSpeech="partOfSpeech"
                :isActive="activePartOfSpeech === `${cluster.clusterId}-${partOfSpeech.type}`"
                :cardVariant="cardVariant"
                @click="$emit('part-of-speech-click', partOfSpeech.type)"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
import { HoverCard, HoverCardTrigger } from '@/components/ui';
import { ShimmerText } from '@/components/custom/animation';
import { formatClusterLabel } from '@/components/custom/definition/utils';
import SidebarHoverCard from './SidebarHoverCard.vue';
import SidebarPartOfSpeech from './SidebarPartOfSpeech.vue';
import type { SidebarCluster } from '../types';

interface Props {
    cluster: SidebarCluster;
    isActive: boolean;
    activePartOfSpeech: string;
    cardVariant?: string;
}

defineProps<Props>();

defineEmits<{
    'cluster-click': [];
    'part-of-speech-click': [partOfSpeech: string];
}>();
</script>