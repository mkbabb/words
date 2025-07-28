<template>
    <button
        @click="$emit('click', item)"
        :class="[
            'group flex w-full items-center justify-between rounded-md px-3 py-2',
            'transition-all duration-200',
            'hover:bg-muted/50',
            'active:scale-[0.98]',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1',
            'text-left'
        ]"
    >
        <div class="min-w-0 flex-1">
            <p class="font-medium text-sm">{{ title }}</p>
            <p v-if="subtitle" class="text-xs text-muted-foreground mt-0.5">
                {{ subtitle }}
            </p>
        </div>
        <span 
            v-if="timestamp"
            class="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity duration-200 ml-2 flex-shrink-0"
        >
            {{ formatTimeDisplay(timestamp) }}
        </span>
    </button>
</template>

<script setup lang="ts">
import { formatTimeDisplay } from '@/utils/time';

interface Props {
    item: any;
    title: string;
    subtitle?: string;
    timestamp?: Date | string;
}

defineProps<Props>();

defineEmits<{
    click: [item: any];
}>();
</script>