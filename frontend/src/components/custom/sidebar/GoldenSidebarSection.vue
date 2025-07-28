<template>
    <AccordionItem :value="value" class="border-b-0">
        <AccordionTrigger
            :class="[
                'group flex w-full items-center justify-between px-0 py-3',
                'hover:no-underline hover:bg-transparent',
                'transition-all duration-200',
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
                    'space-y-1 rounded-lg p-2',
                    'bg-yellow-50/50 dark:bg-yellow-900/10',
                    'border border-yellow-200/50 dark:border-yellow-700/30',
                    items.length > 15 ? 'max-h-[60vh] overflow-y-auto scrollbar-thin pr-2' : ''
                ]"
            >
                <slot :items="items" />
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

<style scoped>
.scrollbar-thin {
    scrollbar-width: thin;
    scrollbar-color: hsl(var(--border) / 0.3) transparent;
}

.scrollbar-thin::-webkit-scrollbar {
    width: 4px;
}

.scrollbar-thin::-webkit-scrollbar-track {
    background: transparent;
}

.scrollbar-thin::-webkit-scrollbar-thumb {
    background: hsl(var(--border) / 0.3);
    border-radius: 2px;
}
</style>