<template>
    <div
        :class="[
            'absolute z-20 flex items-center gap-1',
            aiMode ? 'right-2 bottom-2' : 'top-1/2 right-2 -translate-y-1/2',
        ]"
    >
        <!-- Expand Button -->
        <Transition
            enter-active-class="transition-all duration-200 ease-out"
            leave-active-class="transition-all duration-200 ease-in"
            enter-from-class="opacity-0 scale-90"
            leave-to-class="opacity-0 scale-90"
        >
            <button
                v-if="aiMode && scrollProgress < 0.3"
                :class="[
                    'rounded-md p-1 transition-all duration-200',
                    'hover:scale-105 focus:ring-2 focus:ring-primary/50 focus:outline-none',
                    aiMode
                        ? 'bg-amber-100/80 hover:bg-amber-200/80 dark:bg-amber-900/40 dark:hover:bg-amber-800/40'
                        : 'bg-muted/50 hover:bg-muted/80',
                ]"
                :style="{
                    opacity: 1 - scrollProgress * 3,
                    transform: `scale(${1 - scrollProgress * 0.5})`,
                }"
                @click.stop="$emit('expand')"
                title="Expand for longer input"
            >
                <Maximize2
                    :class="[
                        'h-4 w-4',
                        aiMode
                            ? 'text-amber-700 hover:text-amber-800 dark:text-amber-300 dark:hover:text-amber-200'
                            : 'text-foreground/70 hover:text-foreground',
                    ]"
                />
            </button>
        </Transition>

        <!-- Clear Button -->
        <Transition
            enter-active-class="transition-all duration-200 ease-out"
            leave-active-class="transition-all duration-200 ease-in"
            enter-from-class="opacity-0 scale-90"
            leave-to-class="opacity-0 scale-90"
        >
            <button
                v-if="showClear"
                @click.stop="$emit('clear')"
                :class="[
                    'rounded-md p-1 transition-all duration-200',
                    'hover:scale-105 focus:ring-2 focus:ring-primary/50 focus:outline-none',
                    aiMode
                        ? 'bg-transparent hover:bg-amber-100/80 dark:hover:bg-amber-900/40'
                        : 'bg-transparent hover:bg-muted/80',
                ]"
                title="Clear search"
            >
                <X
                    :class="[
                        'h-4 w-4',
                        aiMode
                            ? 'text-amber-700 hover:text-amber-800 dark:text-amber-300 dark:hover:text-amber-200'
                            : 'text-foreground/50 hover:text-foreground/70',
                    ]"
                />
            </button>
        </Transition>
    </div>
</template>

<script setup lang="ts">
import { Maximize2, X } from 'lucide-vue-next';

defineProps<{
    aiMode: boolean;
    showClear: boolean;
    scrollProgress: number;
}>();

defineEmits<{
    expand: [];
    clear: [];
}>();
</script>
