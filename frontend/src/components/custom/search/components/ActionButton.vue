<template>
    <button
        :class="[
            'group relative flex items-center justify-center',
            'rounded-full p-4 transition-all duration-200 sm:p-3.5',
            'hover:scale-105 active:scale-95',
            'focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-2 focus-visible:outline-none',
            'min-w-[3.5rem] sm:min-w-[3rem]',
            variantClasses,
        ]"
        v-bind="$attrs"
    >
        <span class="transition-transform duration-200 group-hover:scale-110">
            <slot />
        </span>
    </button>
</template>

<script setup lang="ts">
import { computed } from 'vue';

type Variant = 'default' | 'primary' | 'danger' | 'secondary';

interface ActionButtonProps {
    variant?: Variant;
}

const props = withDefaults(defineProps<ActionButtonProps>(), {
    variant: 'default',
});

const variantClasses = computed(() => {
    const variants: Record<Variant, string> = {
        default:
            'bg-card/60 backdrop-blur-sm border border-border/30 text-muted-foreground hover:bg-card/80 hover:text-foreground hover:border-border/50 shadow-sm',
        primary:
            'bg-foreground/90 backdrop-blur-sm border border-foreground/20 text-background hover:bg-foreground hover:border-foreground/30 shadow-sm',
        danger: 'bg-red-500/10 backdrop-blur-sm border border-red-500/20 text-red-600 dark:text-red-400 hover:bg-red-500/20 hover:border-red-500/30 hover:text-red-700 dark:hover:text-red-300 shadow-sm',
        secondary:
            'bg-card/50 backdrop-blur-sm border border-border/25 text-muted-foreground hover:bg-card/75 hover:text-foreground hover:border-border/45 shadow-sm',
    };

    return variants[props.variant];
});
</script>
