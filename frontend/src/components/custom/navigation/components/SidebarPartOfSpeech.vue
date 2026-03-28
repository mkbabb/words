<template>
    <HoverCard :open-delay="200" :close-delay="100">
        <HoverCardTrigger>
            <button
                @click="$emit('click')"
                :data-toc-id="`${clusterId}-${partOfSpeech.type}`"
                :data-sidebar-pos="`${clusterId}-${partOfSpeech.type}`"
                :class="[
                    'group flex h-8 w-full cursor-pointer items-center justify-between rounded-md border px-2.5 py-1.5 transition-[background-color,border-color,color,box-shadow,transform] duration-250 ease-apple-spring transform-gpu',
                    isActive
                        ? 'border-primary/30 bg-primary/10 text-foreground shadow-sm dark:bg-primary/20'
                        : 'border-border/40 bg-background/96 text-foreground/70 hover:border-border/60 hover:bg-background hover:text-foreground/90 hover:shadow-sm dark:bg-background/80 dark:hover:bg-background/85'
                ]"
            >
                <span class="text-xs font-medium uppercase tracking-wider">{{ partOfSpeech.type }}</span>
                <div class="flex items-center gap-2">
                    <span class="text-xs opacity-70">{{ partOfSpeech.count }}</span>
                    <div
                        v-if="isActive"
                        class="h-1.5 w-1.5 flex-shrink-0 animate-pulse rounded-full bg-primary transition-[transform,opacity] duration-300 ease-apple-smooth"
                    />
                </div>
            </button>
        </HoverCardTrigger>
        <HoverCardContent
            :class="cn(
                'themed-hovercard z-hovercard w-80 glass-elevated bg-background/96 shadow-cartoon-lg',
                cardVariant !== 'default' ? 'shadow-cartoon-sm' : ''
            )"
            :data-theme="cardVariant || 'default'"
            side="right"
            align="start"
        >
            <PartOfSpeechPreview
                :clusterId="clusterId"
                :partOfSpeech="partOfSpeech"
                :clusterDescription="clusterDescription"
            />
        </HoverCardContent>
    </HoverCard>
</template>

<script setup lang="ts">
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@mkbabb/glass-ui';
import { cn } from '@mkbabb/glass-ui';
import PartOfSpeechPreview from './PartOfSpeechPreview.vue';

interface Props {
    clusterId: string;
    partOfSpeech: { type: string; count: number };
    isActive: boolean;
    cardVariant?: string;
    clusterDescription?: string;
}

defineProps<Props>();

defineEmits<{
    click: [];
}>();
</script>
