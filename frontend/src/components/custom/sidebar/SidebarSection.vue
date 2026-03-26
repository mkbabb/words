<template>
    <AccordionItem :value="value" class="border-b-0">
        <AccordionTrigger
            :class="[
                'group flex w-full items-center justify-between px-0 py-3',
                'hover:no-underline hover:bg-transparent',
                'transition-fast',
                'text-sm font-medium text-foreground/80 hover:text-foreground',
                '[&[data-state=open]>svg]:rotate-90'
            ]"
        >
            <span class="flex items-center gap-2 text-left">
                <component :is="icon" v-if="icon" class="h-4 w-4" />
                {{ title }}
                <span v-if="count" class="text-xs text-muted-foreground">({{ count }})</span>
            </span>
        </AccordionTrigger>
        <AccordionContent class="pb-2 pt-0">
            <div
                v-if="items.length > 0"
                :class="[
                    'space-y-1 rounded-xl border border-border/30 bg-background/96 p-1.5 shadow-sm',
                    items.length > 10 ? 'max-h-[40vh] overflow-y-auto scrollbar-thin pr-2' : ''
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
