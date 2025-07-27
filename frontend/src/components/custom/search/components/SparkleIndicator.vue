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
            class="absolute -top-2 -left-2 z-50 pointer-events-none"
        >
            <div class="relative">
                <Sparkles 
                    :size="size" 
                    class="text-amber-600 dark:text-amber-400 animate-pulse drop-shadow-lg fill-amber-600 dark:fill-amber-400"
                />
                <Sparkles 
                    :size="size" 
                    class="absolute inset-0 text-amber-300 dark:text-amber-600 opacity-50 animate-spin-slow fill-amber-300 dark:fill-amber-600"
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
    size: 28
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