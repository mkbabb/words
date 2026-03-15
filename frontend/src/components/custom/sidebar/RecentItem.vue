<template>
    <HoverCard v-if="$slots.hover" :open-delay="300" :close-delay="100">
        <HoverCardTrigger as-child>
            <button
                @click="$emit('click', item)"
                :class="buttonClasses"
            >
                <div class="min-w-0 flex-1">
                    <p class="truncate text-sm font-medium text-foreground">
                        {{ title }}
                    </p>
                    <p v-if="subtitle" class="truncate text-xs text-muted-foreground mt-0.5">
                        {{ subtitle }}
                    </p>
                </div>
                <div class="ml-2 flex items-center gap-2 text-xs text-muted-foreground">
                    <span v-if="metadata">{{ metadata }}</span>
                    <span v-if="timestamp">{{ formatRelativeTime(timestamp) }}</span>
                </div>
            </button>
        </HoverCardTrigger>
        <HoverCardContent side="left" align="start" class="w-72">
            <slot name="hover" />
        </HoverCardContent>
    </HoverCard>
    <button
        v-else
        @click="$emit('click', item)"
        :class="buttonClasses"
    >
        <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-foreground">
                {{ title }}
            </p>
            <p v-if="subtitle" class="truncate text-xs text-muted-foreground mt-0.5">
                {{ subtitle }}
            </p>
        </div>
        <div class="ml-2 flex items-center gap-2 text-xs text-muted-foreground">
            <span v-if="metadata">{{ metadata }}</span>
            <span v-if="timestamp">{{ formatRelativeTime(timestamp) }}</span>
        </div>
    </button>
</template>

<script setup lang="ts">
import { formatRelativeTime } from '@/utils/time';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';

interface Props {
    item: any;
    title: string;
    subtitle?: string;
    metadata?: string;
    timestamp?: Date | string;
}

defineProps<Props>();

defineEmits<{
    click: [item: any];
}>();

const buttonClasses = [
    'group flex w-full items-center justify-between rounded-md px-3 py-2',
    'transition-colors duration-200',
    'hover:bg-muted/50',
    'active:scale-[0.98]',
    'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1',
    'text-left',
];
</script>
