<template>
    <div
        :class="[
            'group flex items-center gap-3 px-4 py-2.5 cursor-pointer select-none',
            'border-l-[3px] transition-colors duration-100',
            masteryBorderClass,
            isSelected
                ? 'bg-primary/6 dark:bg-primary/4'
                : 'hover:bg-muted/30',
        ]"
        @click="handleClick"
    >
        <!-- Word + inline telemetry -->
        <div class="flex-1 min-w-0 flex items-baseline gap-2 sm:gap-3 flex-wrap">
            <!-- Word -->
            <span class="font-serif text-base sm:text-lg leading-snug text-foreground break-all">
                {{ word.word.toLowerCase() }}
            </span>

            <!-- Inline pills -->
            <div class="flex items-center gap-1 flex-wrap">
                <span v-if="word.frequency > 1" class="pill bg-muted/60 text-muted-foreground">
                    {{ word.frequency }}×
                </span>
                <span v-if="cardState" :class="['pill', cardStateBadgeClass]">
                    {{ cardStateLabel }}
                </span>
                <span v-if="isDue" class="pill bg-primary/10 text-primary">due</span>
                <span v-if="word.review_data?.is_leech" class="pill bg-destructive/10 text-destructive">leech</span>
            </div>
        </div>

        <!-- Right: telemetry numbers + mastery -->
        <div class="flex items-center gap-3 shrink-0 text-[11px] text-muted-foreground/60 tabular-nums">
            <span v-if="word.review_data && word.review_data.repetitions > 0">
                {{ word.review_data.ease_factor.toFixed(2) }}
            </span>
            <span v-if="word.review_data && word.review_data.interval > 0">
                {{ formatIntervalShort(word.review_data.interval) }}
            </span>
            <span v-if="word.temperature === 'hot'" class="h-1.5 w-1.5 rounded-full bg-orange-400" />
            <span
                v-if="word.mastery_level && word.mastery_level !== 'default'"
                :class="['pill font-semibold capitalize', masteryBadgeClass]"
            >
                {{ word.mastery_level }}
            </span>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { WordListItem } from '@/types';

const props = withDefaults(defineProps<{
    word: WordListItem;
    index: number;
    isSelected?: boolean;
}>(), {
    isSelected: false,
});

const emit = defineEmits<{
    click: [word: WordListItem, index: number, event: MouseEvent];
}>();

function handleClick(event: MouseEvent) {
    emit('click', props.word, props.index, event);
}

const cardState = computed(() => props.word.review_data?.card_state);

const cardStateLabel = computed(() => {
    const labels: Record<string, string> = {
        new: 'New', learning: 'Learning', young: 'Young',
        mature: 'Mature', relearning: 'Relearning',
    };
    return labels[cardState.value ?? ''] ?? '';
});

const cardStateBadgeClass = computed(() => {
    const classes: Record<string, string> = {
        new: 'bg-muted/80 text-muted-foreground',
        learning: 'bg-[var(--card-state-learning)]/10 text-[var(--card-state-learning)]',
        young: 'bg-[var(--card-state-young)]/10 text-[var(--card-state-young)]',
        mature: 'bg-[var(--card-state-mature)]/10 text-[var(--card-state-mature)]',
        relearning: 'bg-[var(--card-state-relearning)]/10 text-[var(--card-state-relearning)]',
    };
    return classes[cardState.value ?? ''] ?? '';
});

const masteryBorderClass = computed(() => {
    const map: Record<string, string> = {
        gold: 'border-l-[var(--mastery-gold)]',
        silver: 'border-l-[var(--mastery-silver)]',
        bronze: 'border-l-[var(--mastery-bronze)]',
    };
    return map[props.word.mastery_level ?? ''] ?? 'border-l-transparent';
});

const masteryBadgeClass = computed(() => {
    const map: Record<string, string> = {
        gold: 'bg-[var(--mastery-gold)]/10 text-[var(--mastery-gold)]',
        silver: 'bg-[var(--mastery-silver)]/15 text-[var(--mastery-silver)]',
        bronze: 'bg-[var(--mastery-bronze)]/10 text-[var(--mastery-bronze)]',
    };
    return map[props.word.mastery_level ?? ''] ?? '';
});

const isDue = computed(() => {
    const next = props.word.review_data?.next_review_date;
    if (!next) return false;
    return new Date(next) <= new Date();
});

function formatIntervalShort(interval: number): string {
    if (interval < 1) return `${Math.round(interval * 24 * 60)}m`;
    if (interval < 30) return `${Math.round(interval)}d`;
    if (interval < 365) return `${Math.round(interval / 30)}mo`;
    return `${(interval / 365).toFixed(1)}y`;
}
</script>

<style scoped>
.pill {
    display: inline-flex;
    align-items: center;
    border-radius: 9999px;
    padding: 1px 6px;
    font-size: var(--type-micro);
    font-weight: 500;
    line-height: 1.4;
}
</style>
