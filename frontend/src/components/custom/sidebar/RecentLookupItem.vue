<template>
    <HoverCard :open-delay="600">
        <HoverCardTrigger as-child>
            <button
                @click="$emit('click', item)"
                :class="[
                    'group flex w-full items-start gap-3 rounded-lg border px-3 py-2',
                    'transition-all duration-200',
                    'hover:bg-muted/50 hover:scale-[1.02] hover:border-primary/20',
                    'active:scale-[0.98]',
                    'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1',
                    'text-left'
                ]"
            >
                <div class="min-w-0 flex-1">
                    <p class="font-medium text-sm">{{ item.word }}</p>
                    <p v-if="subtitle" class="text-xs text-muted-foreground line-clamp-2 mt-0.5">
                        {{ subtitle }}
                    </p>
                </div>
            </button>
        </HoverCardTrigger>
        <HoverCardContent side="left" align="start" class="w-80">
            <div class="space-y-3">
                <div>
                    <h4 class="text-base font-semibold">{{ item.word }}</h4>
                    <p v-if="subtitle" class="text-sm text-muted-foreground mt-1">{{ subtitle }}</p>
                </div>
                <div class="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{{ item.definitions?.length || 0 }} definitions</span>
                    <span>{{ formatRelativeTime(item.timestamp) }}</span>
                </div>
            </div>
        </HoverCardContent>
    </HoverCard>
</template>

<script setup lang="ts">
import { formatRelativeTime } from '@/utils/time';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import type { SynthesizedDictionaryEntry } from '@/types';

interface Props {
    item: SynthesizedDictionaryEntry;
    subtitle?: string;
}

defineProps<Props>();

defineEmits<{
    click: [item: SynthesizedDictionaryEntry];
}>();
</script>