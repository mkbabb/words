<template>
    <Transition
        enter-active-class="transition-smooth"
        leave-active-class="transition-[opacity,transform] duration-normal ease-in"
        enter-from-class="opacity-0 scale-0"
        enter-to-class="opacity-100 scale-100"
        leave-from-class="opacity-100 scale-100"
        leave-to-class="opacity-0 scale-0"
    >
        <div
            v-if="show"
            class="pointer-events-none absolute -top-2 -left-2 z-overlay"
        >
            <div class="relative">
                <Sparkles
                    :size="size"
                    class="animate-pulse fill-[var(--color-gold)] text-[var(--color-gold)] drop-shadow-lg dark:fill-[var(--color-gold)] dark:text-[var(--color-gold)]"
                />
                <Sparkles
                    :size="size"
                    class="animate-spin-slow absolute inset-0 fill-[var(--color-gold)]/50 text-[var(--color-gold)]/50 opacity-50 dark:fill-[var(--color-gold)]/60 dark:text-[var(--color-gold)]/60"
                />
            </div>
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { Sparkles } from 'lucide-vue-next';

interface SparkleIndicatorProps {
    show: boolean;
    size?: number;
}

withDefaults(defineProps<SparkleIndicatorProps>(), {
    size: 28,
});
</script>

<style scoped>
@keyframes spin-slow {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}

.animate-spin-slow {
    animation: spin-slow 3s linear infinite;
}
</style>
