<template>
    <button
        :class="[
            'group relative flex items-center justify-center',
            'rounded-xl p-3 transition-all duration-200',
            'hover:scale-105 active:scale-95',
            'focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary/50',
            variantClasses
        ]"
        v-bind="$attrs"
    >
        <span class="group-hover:scale-110 transition-transform duration-200">
            <slot />
        </span>
    </button>
</template>

<script setup lang="ts">
import { computed } from 'vue';

type Variant = 'default' | 'primary' | 'danger';

interface ActionButtonProps {
    variant?: Variant;
}

const props = withDefaults(defineProps<ActionButtonProps>(), {
    variant: 'default'
});

const variantClasses = computed(() => {
    const variants: Record<Variant, string> = {
        default: 'bg-muted hover:bg-muted/80 text-foreground/70 hover:text-foreground',
        primary: 'bg-black dark:bg-white text-white dark:text-black hover:bg-black/90 dark:hover:bg-white/90',
        danger: 'bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-500 hover:bg-red-100 dark:hover:bg-red-500/20 hover:text-red-700 dark:hover:text-red-400'
    };
    
    return variants[props.variant];
});
</script>