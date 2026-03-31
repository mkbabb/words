<template>
    <component
        :is="as"
        :class="[
            'group/stack relative isolate flex',
            direction === 'vertical' ? 'flex-col' : 'items-center',
            reversed ? (direction === 'vertical' ? 'flex-col-reverse' : 'flex-row-reverse') : '',
        ]"
    >
        <!-- Visible icons (up to maxVisible) -->
        <template v-for="(item, i) in visibleItems" :key="keyFn?.(item, i) ?? i">
            <div
                :class="[
                    sizeClass,
                    'relative flex items-center justify-center rounded-full transform-gpu',
                    'transition-[transform,box-shadow,opacity] duration-fast ease-spring-snappy',
                    i > 0 ? overlapClass : '',
                    expandOnHover && i > 0
                        ? direction === 'vertical'
                            ? 'group-hover/stack:translate-y-1.5 group-hover/stack:scale-105'
                            : 'group-hover/stack:translate-x-1.5 group-hover/stack:scale-105'
                        : '',
                ]"
                :style="{ zIndex: visibleItems.length + 1 - i }"
            >
                <slot name="icon" :item="item" :index="i" />
            </div>
        </template>

        <!-- Overflow indicator (+N) when items exceed maxVisible -->
        <div
            v-if="overflowCount > 0"
            :class="[
                sizeClass,
                'relative flex items-center justify-center rounded-full',
                'border-2 border-background bg-background/96 text-xs font-semibold text-muted-foreground/60 shadow-cartoon-sm',
                'transform-gpu transition-[background-color,color,transform,box-shadow] duration-fast ease-spring-snappy',
                'hover:bg-background hover:text-muted-foreground hover:shadow-cartoon-md',
                overlapClass,
                expandOnHover
                    ? direction === 'vertical'
                        ? 'group-hover/stack:translate-y-1.5 group-hover/stack:scale-105'
                        : 'group-hover/stack:translate-x-1.5 group-hover/stack:scale-105'
                    : '',
            ]"
            :style="{ zIndex: 1 }"
        >
            <slot name="overflow" :count="overflowCount">
                +{{ overflowCount }}
            </slot>
        </div>

        <!-- Info/detail trigger — shown when items fit within maxVisible (no overflow) -->
        <div
            v-if="overflowCount === 0 && $slots.info"
            :style="{ zIndex: 0 }"
        >
            <slot name="info" />
        </div>
    </component>
</template>

<script setup lang="ts" generic="T">
import { computed } from 'vue';

interface StackedIconGroupProps {
    /** Items to display */
    items: T[];
    /** Max visible icons before showing +N overflow */
    maxVisible?: number;
    /** Stack direction */
    direction?: 'horizontal' | 'vertical';
    /** Reverse the visual order */
    reversed?: boolean;
    /** Icon size */
    size?: 'sm' | 'md' | 'lg';
    /** Expand icons on group hover */
    expandOnHover?: boolean;
    /** Root element tag */
    as?: string;
    /** Key extraction function for v-for */
    keyFn?: (item: T, index: number) => string | number;
}

const props = withDefaults(defineProps<StackedIconGroupProps>(), {
    maxVisible: 3,
    direction: 'horizontal',
    reversed: false,
    size: 'md',
    expandOnHover: true,
    as: 'div',
});

const sizeClass = computed(() => {
    switch (props.size) {
        case 'sm': return 'h-6 w-6';
        case 'md': return 'h-8 w-8';
        case 'lg': return 'h-10 w-10';
    }
});

const overlapClass = computed(() => {
    if (props.direction === 'vertical') {
        switch (props.size) {
            case 'sm': return '-mt-1.5';
            case 'md': return '-mt-2';
            case 'lg': return '-mt-2.5';
        }
    }
    switch (props.size) {
        case 'sm': return '-ml-1.5';
        case 'md': return '-ml-2';
        case 'lg': return '-ml-2.5';
    }
});

const visibleItems = computed(() =>
    props.items.slice(0, props.maxVisible),
);

const overflowCount = computed(() =>
    Math.max(0, props.items.length - props.maxVisible),
);
</script>
