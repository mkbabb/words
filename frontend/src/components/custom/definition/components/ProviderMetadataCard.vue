<template>
    <div
        class="flex items-center gap-3 rounded-xl px-2.5 py-2 transition-colors duration-150"
        :class="[
            interactive ? 'cursor-pointer' : 'cursor-default',
            isActive
                ? 'bg-primary/10 font-medium text-foreground hover:bg-primary/15'
                : interactive
                    ? 'text-foreground/80 hover:bg-muted/80 hover:text-foreground'
                    : 'text-foreground/80',
        ]"
    >
        <!-- Provider icon -->
        <component
            :is="getProviderIcon(provider)"
            :size="16"
            class="flex-shrink-0"
            :class="isActive ? 'text-foreground' : 'text-muted-foreground'"
        />

        <!-- Name + metadata -->
        <div class="flex-1 min-w-0 space-y-1">
            <div class="flex items-center gap-2">
                <span class="text-sm truncate">{{ displayName }}</span>
                <span
                    v-if="version"
                    class="font-mono text-xs text-muted-foreground/50"
                >v{{ version }}</span>
            </div>

            <!-- Richness bar + stats row -->
            <div v-if="richnessScore != null" class="flex items-center gap-2">
                <!-- Mini richness bar -->
                <div class="relative h-1.5 flex-1 rounded-full bg-muted/60 overflow-hidden">
                    <div
                        class="absolute inset-y-0 left-0 rounded-full transition-all duration-300"
                        :style="{
                            width: `${Math.round(richnessScore * 100)}%`,
                            backgroundColor: richnessToColor(richnessScore),
                        }"
                    />
                </div>
                <span
                    class="text-micro font-medium tabular-nums whitespace-nowrap"
                    :style="{ color: richnessToColor(richnessScore) }"
                >{{ richnessToLabel(richnessScore) }}</span>
            </div>

            <!-- Definition count + fetch date -->
            <div class="flex items-center gap-2 text-micro text-muted-foreground/70">
                <span v-if="definitionCount != null">{{ definitionCount }} def{{ definitionCount === 1 ? '' : 's' }}</span>
                <span v-if="definitionCount != null && relativeDate">&middot;</span>
                <span v-if="relativeDate">{{ relativeDate }}</span>
            </div>
        </div>

        <!-- Active indicator -->
        <div
            v-if="isActive"
            class="h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0"
        />
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { getProviderIcon } from '../utils/providers';
import { richnessToColor, richnessToLabel } from '../utils/richness';

interface Props {
    provider: string;
    displayName: string;
    isActive?: boolean;
    interactive?: boolean;
    version?: string;
    richnessScore?: number | null;
    definitionCount?: number | null;
    fetchedAt?: string | null;
}

const props = withDefaults(defineProps<Props>(), {
    isActive: false,
    interactive: true,
    richnessScore: null,
    definitionCount: null,
    fetchedAt: null,
});

const relativeDate = computed(() => {
    if (!props.fetchedAt) return null;
    const date = new Date(props.fetchedAt);
    if (isNaN(date.getTime())) return null;
    const now = Date.now();
    const diffMs = now - date.getTime();
    const diffDays = Math.floor(diffMs / 86_400_000);
    if (diffDays === 0) return 'today';
    if (diffDays === 1) return 'yesterday';
    if (diffDays < 30) return `${diffDays}d ago`;
    const diffMonths = Math.floor(diffDays / 30);
    if (diffMonths < 12) return `${diffMonths}mo ago`;
    return `${Math.floor(diffMonths / 12)}y ago`;
});
</script>
