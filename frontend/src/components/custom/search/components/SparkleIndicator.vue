<template>
    <Transition
        enter-active-class="transition-all duration-500 ease-out"
        leave-active-class="transition-all duration-300 ease-in"
        enter-from-class="opacity-0 scale-0"
        enter-to-class="opacity-100 scale-100"
        leave-from-class="opacity-100 scale-100"
        leave-to-class="opacity-0 scale-0"
    >
        <div
            v-if="show"
            class="pointer-events-none absolute -top-2 -left-2 z-50"
        >
            <div class="relative">
                <Sparkles
                    :size="size"
                    class="animate-pulse fill-amber-600 text-amber-600 drop-shadow-lg dark:fill-amber-400 dark:text-amber-400"
                />
                <Sparkles
                    :size="size"
                    class="animate-spin-slow absolute inset-0 fill-amber-300 text-amber-300 opacity-50 dark:fill-amber-600 dark:text-amber-600"
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
