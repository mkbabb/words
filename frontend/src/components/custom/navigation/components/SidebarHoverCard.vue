<template>
    <HoverCardContent
        :class="cn(
            'themed-hovercard z-hovercard max-w-[min(384px,90vw)] w-96 glass-heavy bg-background/96 shadow-cartoon-lg',
            variant !== 'default' ? 'shadow-cartoon-sm' : ''
        )"
        :data-theme="variant || 'default'"
        :side="side"
        :align="align"
    >
        <div class="space-y-3">
            <!-- Cluster Header -->
            <div>
                <h4 class="mb-1 text-base font-medium uppercase">
                    {{ cluster.clusterName }}
                </h4>
                <p class="text-sm text-muted-foreground">
                    {{ cluster.clusterDescription }}
                </p>
            </div>

            <!-- Definition Previews -->
            <div v-if="cluster.definitions && cluster.definitions.length > 0" class="space-y-2">
                <div
                    v-for="(def, i) in cluster.definitions"
                    :key="i"
                    class="rounded-lg border border-border/30 bg-muted/20 px-3 py-2"
                >
                    <div class="mb-0.5 text-xs font-medium text-primary/80">
                        {{ def.partOfSpeech }}
                    </div>
                    <p class="text-xs leading-relaxed text-foreground/80 line-clamp-2">
                        {{ def.text }}
                    </p>
                    <div v-if="def.synonyms.length > 0" class="mt-1 flex flex-wrap gap-1">
                        <span
                            v-for="syn in def.synonyms"
                            :key="syn"
                            class="rounded-md bg-muted/50 px-1.5 py-0.5 text-micro text-muted-foreground"
                        >
                            {{ syn }}
                        </span>
                    </div>
                </div>
            </div>

            <!-- Metadata -->
            <div class="space-y-1.5 border-t border-border/30 pt-2">
                <div class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">Relevance</span>
                    <span class="text-xs font-medium">
                        {{ Math.round((cluster.maxRelevancy || 1.0) * 100) }}%
                    </span>
                </div>
                <div class="flex items-center justify-between">
                    <span class="text-xs text-muted-foreground">Definitions</span>
                    <span class="text-xs font-medium">{{ totalDefinitions }}</span>
                </div>
            </div>
        </div>
    </HoverCardContent>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { HoverCardContent } from '@/components/ui';
import { cn } from '@/utils';
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
