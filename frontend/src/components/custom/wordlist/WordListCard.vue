<template>
    <BaseWordCard
        :word="word.word ?? ''"
        :variant="word.mastery_level"
        :class-name="scoreClass"
        linkable
        @click="$emit('click', word)"
        @lookup="$emit('lookup', word)"
    >
        <template #overlay>
            <div class="opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                <DropdownMenu>
                    <DropdownMenuTrigger as-child @click.stop>
                        <Button
                            variant="ghost"
                            size="sm"
                            class="h-5 w-5 bg-background/80 p-0 backdrop-blur-sm"
                        >
                            <MoreVertical class="h-3 w-3" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                        <DropdownMenuItem @click.stop="$emit('review', word, 4)">
                            <BookOpen class="mr-2 h-3 w-3" />
                            Review
                        </DropdownMenuItem>
                        <DropdownMenuItem @click.stop="$emit('edit', word)">
                            <Edit2 class="mr-2 h-3 w-3" />
                            Edit Notes
                        </DropdownMenuItem>
                        <DropdownMenuItem @click.stop="$emit('visited', word)">
                            <Eye class="mr-2 h-3 w-3" />
                            Mark Visited
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                            @click.stop="$emit('remove', word)"
                            class="text-destructive"
                        >
                            <Trash2 class="mr-2 h-3 w-3" />
                            Remove
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </template>

        <template #meta>
            <!-- Progress bar -->
            <div class="mb-1">
                <div class="relative h-1 w-full overflow-hidden rounded-full bg-muted">
                    <div
                        class="absolute inset-y-0 left-0 transition-all duration-500 rounded-full"
                        :style="{ width: `${progressPercentage}%`, background: rainbowGradient }"
                    />
                </div>
            </div>

            <!-- Word metadata -->
            <div class="flex items-center gap-1 text-[11px] text-muted-foreground">
                <span>{{ word.frequency }}x</span>
                <span>&middot;</span>
                <span>{{ getMasteryLabel(word.mastery_level) }}</span>
                <template v-if="stateLabel">
                    <span>&middot;</span>
                    <span :class="stateColorClass">{{ stateLabel }}</span>
                </template>
                <span
                    v-if="isDueForReview"
                    class="ml-0.5 inline-flex items-center rounded-full px-1.5 py-0.5 text-micro font-medium"
                    style="background: color-mix(in srgb, var(--review-again) 15%, transparent); color: var(--review-again);"
                >
                    Due
                </span>
                <span
                    v-if="word.review_data?.is_leech"
                    class="ml-0.5 inline-flex items-center rounded-full bg-destructive/10 px-1.5 py-0.5 text-micro font-medium text-destructive"
                >
                    Leech
                </span>
            </div>
        </template>
    </BaseWordCard>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { BookOpen, Edit2, Eye, MoreVertical, Trash2 } from 'lucide-vue-next';
import { generateRainbowGradient } from '@/utils/animations';
import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuTrigger,
    DropdownMenuItem,
    DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import type { WordListItem } from '@/types';
import BaseWordCard from './BaseWordCard.vue';
import {
    getMasteryLabel,
    getCardStateLabel,
    getCardStateColorClass,
    computeProgress,
} from './utils/formatting';

const props = defineProps<{
    word: WordListItem & { score?: number };
}>();

defineEmits<{
    click: [word: WordListItem];
    lookup: [word: WordListItem];
    review: [word: WordListItem, quality: number];
    edit: [word: WordListItem];
    visited: [word: WordListItem];
    remove: [word: WordListItem];
}>();

const rainbowGradient = generateRainbowGradient(7);

const scoreClass = computed(() => {
    const classes: string[] = [];
    const s = props.word.score ?? 0;
    if (s >= 1.0) classes.push('search-match-gold');
    else if (s >= 0.9) classes.push('search-match-silver');
    else if (s >= 0.8) classes.push('search-match-bronze');

    if (props.word.temperature === 'hot') classes.push('ring-1 ring-orange-400/20');
    else if (props.word.temperature === 'cold') classes.push('ring-1 ring-blue-400/20');

    return classes.join(' ');
});

const stateLabel = computed(() =>
    getCardStateLabel(props.word.review_data?.card_state)
);

const stateColorClass = computed(() =>
    getCardStateColorClass(props.word.review_data?.card_state)
);

const isDueForReview = computed(() => {
    const reviewDate = props.word.review_data?.next_review_date;
    if (!reviewDate) return false;
    return new Date(reviewDate) <= new Date();
});

const progressPercentage = computed(() =>
    computeProgress(props.word.mastery_level, props.word.review_data?.repetitions ?? 0)
);
</script>

<style>
/* Search match highlighting borders (colocated — sole consumer) */
.search-match-gold {
    border-width: 2px;
    border-color: rgb(252 211 77 / 0.3);
    position: relative;
    overflow: hidden;
}

.search-match-silver {
    border-width: 2px;
    border-color: rgb(209 213 219 / 0.3);
    position: relative;
    overflow: hidden;
}

.search-match-bronze {
    border-width: 2px;
    border-color: rgb(253 186 116 / 0.3);
    position: relative;
    overflow: hidden;
}

.dark .search-match-gold {
    border-color: rgb(251 191 36 / 0.2);
}

.dark .search-match-silver {
    border-color: rgb(156 163 175 / 0.2);
}

.dark .search-match-bronze {
    border-color: rgb(251 146 60 / 0.2);
}

/* Metallic shimmer effect for search match borders */
.search-match-gold::before,
.search-match-silver::before,
.search-match-bronze::before {
    content: '';
    position: absolute;
    top: -2px;
    left: -2px;
    right: -2px;
    bottom: -2px;
    background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(255, 255, 255, 0.4) 45%,
        rgba(255, 255, 255, 0.6) 50%,
        rgba(255, 255, 255, 0.4) 55%,
        transparent 100%
    );
    transform: translateX(-100%);
    animation: border-shimmer 3s ease-in-out infinite;
    pointer-events: none;
    z-index: 1;
    border-radius: inherit;
    mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    mask-composite: xor;
    mask-composite: exclude;
    padding: 2px;
}

/* Different shimmer colors for each metal */
.search-match-gold::before {
    background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(251, 191, 36, 0.4) 45%,
        rgba(251, 191, 36, 0.7) 50%,
        rgba(251, 191, 36, 0.4) 55%,
        transparent 100%
    );
}

.search-match-silver::before {
    background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(229, 231, 235, 0.5) 45%,
        rgba(229, 231, 235, 0.8) 50%,
        rgba(229, 231, 235, 0.5) 55%,
        transparent 100%
    );
}

.search-match-bronze::before {
    background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(251, 146, 60, 0.4) 45%,
        rgba(251, 146, 60, 0.6) 50%,
        rgba(251, 146, 60, 0.4) 55%,
        transparent 100%
    );
}

/* Shimmer animation */
@keyframes border-shimmer {
    0% {
        transform: translateX(-100%);
    }
    100% {
        transform: translateX(200%);
    }
}

@media (prefers-reduced-motion: reduce) {
    .search-match-gold::before,
    .search-match-silver::before,
    .search-match-bronze::before {
        animation: none;
    }
}
</style>
