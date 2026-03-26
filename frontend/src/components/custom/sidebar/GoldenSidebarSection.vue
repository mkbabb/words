<template>
    <AccordionItem :value="value" class="border-b-0">
        <AccordionTrigger
            :class="[
                'group flex w-full items-center justify-between px-0 py-3',
                'hover:no-underline hover:bg-transparent',
                'transition-fast',
                'text-sm font-medium text-yellow-600 dark:text-yellow-400 hover:text-yellow-700 dark:hover:text-yellow-300',
                '[&[data-state=open]>svg]:rotate-90'
            ]"
        >
            <span class="flex items-center gap-2 text-left">
                <component :is="icon" v-if="icon" class="h-4 w-4" />
                {{ title }}
                <span v-if="count" class="text-xs text-yellow-600/70 dark:text-yellow-400/70">({{ count }})</span>
            </span>
        </AccordionTrigger>
        <AccordionContent class="pb-2 pt-0">
            <div
                v-if="items.length > 0"
                :class="[
                    'space-y-1 rounded-xl border p-2 shadow-sm',
                    'bg-yellow-50/80 dark:bg-yellow-900/15',
                    'border-yellow-200/60 dark:border-yellow-700/30',
                    items.length > 15 ? 'max-h-[60vh] overflow-y-auto scrollbar-thin pr-2' : ''
                ]"
            >
                <div v-for="(item, index) in items" :key="(item as any).id ?? (item as any).word ?? index">
                    <slot name="item" :item="item" />
                </div>
            </div>
            <div v-else class="py-3 text-center text-sm text-muted-foreground">
                {{ emptyMessage }}
            </div>
        </AccordionContent>
    </AccordionItem>
</template>

<script setup lang="ts">
import { AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion';
import type { Component } from 'vue';

interface Props {
    title: string;
    value: string;
    items: any[];
    count?: number;
    icon?: Component;
    emptyMessage?: string;
}

withDefaults(defineProps<Props>(), {
    emptyMessage: 'No items yet'
});
</script>
