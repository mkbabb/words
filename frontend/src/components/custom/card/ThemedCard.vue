<template>
    <div
        :class="[
            'themed-card themed-shadow-lg flex flex-col gap-6 rounded-xl border bg-card py-6 text-card-foreground ',
            className,
        ]"
        :data-theme="variant || 'default'"
    >
        <!-- Star Icon for Special Variants -->
        <div
            v-if="variant && variant !== 'default'"
            class="absolute top-2 right-2 z-10"
        >
            <StarIcon :variant="variant" />
        </div>

        <!-- Sparkle Animation Overlay -->
        <div v-if="variant && variant !== 'default'" class="themed-sparkle" />

        <!-- Content -->
        <slot />
    </div>
</template>

<script setup lang="ts">
import { toRefs } from 'vue';
import { StarIcon } from '@/components/custom/icons';

type CardVariant = 'default' | 'gold' | 'silver' | 'bronze';

interface ThemedCardProps {
    variant?: CardVariant;
    className?: string;
}

const props = defineProps<ThemedCardProps>();

// Clean prop handling
const { variant, className } = toRefs(props);
</script>
