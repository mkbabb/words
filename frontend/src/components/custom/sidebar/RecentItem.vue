<template>
    <button
        @click="$emit('click', item)"
        :class="[
            'group flex w-full items-center justify-between rounded-md px-3 py-2',
            'transition-all duration-200',
            'hover:bg-muted/50 hover:scale-[1.02]',
            'active:scale-[0.98]',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1'
        ]"
    >
        <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium text-foreground">
                {{ title }}
            </p>
            <p v-if="subtitle" class="truncate text-xs text-muted-foreground">
                {{ subtitle }}
            </p>
        </div>
        <div class="ml-2 flex items-center gap-2 text-xs text-muted-foreground">
            <span v-if="metadata">{{ metadata }}</span>
            <span>{{ formatRelativeTime(timestamp) }}</span>
        </div>
    </button>
</template>

<script setup lang="ts">
import { formatRelativeTime } from '@/utils/time';

interface Props {
    item: any;
    title: string;
    subtitle?: string;
    metadata?: string;
    timestamp: Date | string;
}

defineProps<Props>();

defineEmits<{
    click: [item: any];
}>();
</script>