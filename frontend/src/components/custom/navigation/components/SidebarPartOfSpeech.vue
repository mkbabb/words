<template>
    <HoverCard :open-delay="200" :close-delay="100">
        <HoverCardTrigger>
            <button
                @click="$emit('click')"
                :class="[
                    'group flex h-8 w-full cursor-pointer items-center justify-between rounded-md border px-2.5 py-1.5 transition-all duration-200',
                    isActive
                        ? 'border-primary/30 bg-primary/10 text-foreground shadow-sm dark:bg-primary/20'
                        : 'border-transparent bg-muted/20 text-foreground/70 hover:border-border/40 hover:bg-muted/40 hover:text-foreground/90 dark:bg-muted/10 dark:hover:bg-muted/20'
                ]"
            >
                <span class="text-xs font-medium uppercase tracking-wider">{{ partOfSpeech.type }}</span>
                <div class="flex items-center gap-2">
                    <span class="text-xs opacity-70">{{ partOfSpeech.count }}</span>
                    <div
                        v-if="isActive"
                        class="h-1.5 w-1.5 flex-shrink-0 animate-pulse rounded-full bg-primary transition-all duration-300"
                    />
                </div>
            </button>
        </HoverCardTrigger>
        <HoverCardContent
            :class="cn(
                'themed-hovercard z-[80] w-80',
                cardVariant !== 'default' ? 'themed-shadow-sm' : ''
            )"
            :data-theme="cardVariant || 'default'"
        >
            <PartOfSpeechPreview
                :clusterId="clusterId"
                :partOfSpeech="partOfSpeech"
            />
        </HoverCardContent>
    </HoverCard>
</template>

<script setup lang="ts">
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui';
import { cn } from '@/utils';
import PartOfSpeechPreview from './PartOfSpeechPreview.vue';

interface Props {
    clusterId: string;
    partOfSpeech: { type: string; count: number };
    isActive: boolean;
    cardVariant?: string;
}

defineProps<Props>();

defineEmits<{
    click: [];
}>();
</script>