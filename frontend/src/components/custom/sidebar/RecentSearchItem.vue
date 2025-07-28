<template>
    <HoverCard :open-delay="600">
        <HoverCardTrigger as-child>
            <button
                @click="$emit('click', item)"
                :class="[
                    'group flex w-full items-center justify-between rounded-md px-3 py-2',
                    'transition-all duration-200',
                    'hover:bg-muted/50 hover:scale-[1.02]',
                    'active:scale-[0.98]',
                    'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1',
                    'text-left'
                ]"
            >
                <div class="min-w-0 flex-1">
                    <p class="font-medium text-sm">{{ item.query }}</p>
                    <p v-if="subtitle" class="text-xs text-muted-foreground">
                        {{ subtitle }}
                    </p>
                </div>
            </button>
        </HoverCardTrigger>
        <HoverCardContent side="left" align="start" class="w-64">
            <div class="space-y-2">
                <p class="text-sm font-medium">{{ item.query }}</p>
                <p v-if="subtitle" class="text-xs text-muted-foreground">{{ subtitle }}</p>
                <div class="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{{ item.resultCount || 0 }} results</span>
                    <span>{{ formatRelativeTime(item.timestamp) }}</span>
                </div>
            </div>
        </HoverCardContent>
    </HoverCard>
</template>

<script setup lang="ts">
import { formatRelativeTime } from '@/utils/time';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';

interface SearchItem {
    query: string;
    mode?: string;
    resultCount?: number;
    timestamp: Date | string;
}

interface Props {
    item: SearchItem;
    subtitle?: string;
}

defineProps<Props>();

defineEmits<{
    click: [item: SearchItem];
}>();
</script>