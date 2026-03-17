<template>
    <div class="relative px-6 pb-6 pt-3">
        <!-- Timeline container -->
        <div
            class="relative flex items-center gap-0 overflow-x-auto scrollbar-none py-4"
        >
            <!-- Connecting line -->
            <div
                class="pointer-events-none absolute top-1/2 left-6 right-6 h-px -translate-y-1/2 bg-border/50"
            />

            <div
                v-for="(version, index) in versions"
                :key="version.version"
                :ref="(el) => { if (el) dotRefs[index] = el as HTMLElement }"
                class="group relative z-10 flex shrink-0 cursor-pointer flex-col items-center px-3"
                @click="$emit('select', index)"
            >
                <!-- Dot -->
                <div
                    class="relative flex items-center justify-center rounded-full transition-all duration-300"
                    :class="[
                        index === selectedIndex
                            ? 'h-4 w-4 scale-125 bg-primary shadow-lg shadow-primary/30 ring-2 ring-primary/30 ring-offset-2 ring-offset-background'
                            : version.is_latest
                              ? 'h-2.5 w-2.5 bg-primary/60 ring-1 ring-primary/20 ring-offset-1 ring-offset-background group-hover:bg-primary/80'
                              : 'h-2 w-2 bg-muted-foreground/40 group-hover:bg-muted-foreground/70',
                    ]"
                >
                    <!-- Pulse on selected -->
                    <div
                        v-if="index === selectedIndex"
                        class="absolute inset-0 animate-ping rounded-full bg-primary/20"
                        style="animation-duration: 2s"
                    />
                </div>

                <!-- Version label -->
                <div
                    class="mt-2 flex flex-col items-center transition-opacity duration-200"
                    :class="[
                        index === selectedIndex
                            ? 'opacity-100'
                            : 'opacity-0 group-hover:opacity-100',
                    ]"
                >
                    <span
                        class="whitespace-nowrap font-mono text-micro font-medium"
                        :class="[
                            index === selectedIndex
                                ? 'text-primary'
                                : 'text-muted-foreground',
                        ]"
                    >
                        v{{ version.version }}
                    </span>
                    <span class="whitespace-nowrap text-micro text-muted-foreground/50">
                        {{ formatShortDate(version.created_at) }}
                    </span>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import type { VersionSummary } from '@/types/api';

interface Props {
    versions: VersionSummary[];
    selectedIndex: number;
}

const props = defineProps<Props>();

defineEmits<{
    select: [index: number];
}>();

const dotRefs = ref<Record<number, HTMLElement>>({});

function formatShortDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
    });
}

// Auto-scroll selected dot into view
watch(
    () => props.selectedIndex,
    async () => {
        await nextTick();
        const dot = dotRefs.value[props.selectedIndex];
        if (dot) {
            dot.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        }
    }
);
</script>
