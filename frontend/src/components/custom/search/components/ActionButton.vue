<template>
    <Button
        :variant="variantMap[variant]"
        size="icon"
        :data-state="pressed ? 'on' : 'off'"
        :class="[
            'group relative min-w-[3.5rem] rounded-full sm:min-w-[3rem]',
            'h-14 w-14 sm:h-12 sm:w-12',
        ]"
        v-bind="$attrs"
    >
        <span class="transition-transform duration-200 group-hover:scale-110">
            <slot />
        </span>
    </Button>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Button, type ButtonVariants } from '@/components/ui/button';

type Variant = 'default' | 'primary' | 'danger' | 'secondary';

interface ActionButtonProps {
    variant?: Variant;
    pressed?: boolean;
}

const props = withDefaults(defineProps<ActionButtonProps>(), {
    variant: 'default',
    pressed: false,
});

const variantMap = computed<Record<Variant, ButtonVariants['variant']>>(() => {
    return {
        default: 'glass-subtle',
        primary: 'glass',
        danger: 'danger-subtle',
        secondary: 'outline',
    };
});
</script>
