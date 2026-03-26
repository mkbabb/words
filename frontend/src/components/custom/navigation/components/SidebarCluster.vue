<template>
    <div class="space-y-0">
        <!-- Cluster Header -->
        <HoverCard :open-delay="300" :close-delay="100">
            <HoverCardTrigger as-child>
                <button
                    @click="$emit('cluster-click')"
                    :data-toc-id="cluster.clusterId"
                    :data-sidebar-cluster="cluster.clusterId"
                    :aria-current="isActive ? 'true' : undefined"
                    :class="[
                        'group flex w-full items-center rounded-md px-2 py-1 text-left text-sm transition-[background-color,border-color,color,box-shadow,transform] duration-250 ease-apple-spring focus-ring transform-gpu',
                        isActive
                            ? 'bg-background/96 font-medium text-foreground shadow-sm'
                            : 'bg-background/96 font-normal text-foreground/80 hover:bg-background hover:text-foreground hover:shadow-sm'
                    ]"
                >
                    <div class="min-w-0 flex-1 overflow-hidden text-ellipsis whitespace-nowrap pr-2">
                        <ShimmerText
                            v-if="isActive"
                            :text="cluster.clusterName.toUpperCase()"
                            text-class="themed-cluster-title text-left text-xs font-medium uppercase tracking-wider"
                            :duration="400"
                            :interval="15000"
                        />
                        <span
                            v-else
                            class="themed-cluster-title text-left text-xs font-medium uppercase tracking-wider"
                        >
                            {{ cluster.clusterName.toUpperCase() }}
                        </span>
                    </div>
                    <div
                        v-if="isActive"
                        class="ml-2 h-2 w-2 flex-shrink-0 rounded-full bg-primary/30 transition-[transform,opacity] duration-300 ease-apple-smooth"
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
                :clusterDescription="cluster.clusterDescription"
                @click="$emit('part-of-speech-click', partOfSpeech.type)"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
import { HoverCard, HoverCardTrigger } from '@/components/ui';
import { ShimmerText } from '@/components/custom/animation';
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
