<template>
    <HoverCard :open-delay="300" :close-delay="100">
        <HoverCardTrigger as-child>
            <ThemedCard
                :variant="word.mastery_level"
                :class="[
                    'group ease-apple-spring relative cursor-pointer p-3 transition-all duration-500 hover:scale-[1.02] sm:p-4',
                    (word.score ?? 0) >= 1.0
                        ? 'search-match-gold'
                        : (word.score ?? 0) >= 0.9
                          ? 'search-match-silver'
                          : (word.score ?? 0) >= 0.8
                            ? 'search-match-bronze'
                            : '',
                ]"
                texture-enabled
                texture-type="clean"
                texture-intensity="subtle"
                hide-star
                @click="$emit('click', word)"
            >
                <!-- Main content -->
                <div>
                    <!-- Header with word and metadata -->
                    <div class="mb-3">
                        <div class="mb-2 flex items-center justify-between">
                            <h3
                                class="themed-title truncate text-base font-semibold transition-colors group-hover:text-primary sm:text-xl"
                            >
                                {{ word.word?.toLowerCase() ?? '' }}
                            </h3>
                        </div>

                        <!-- Progress bar below title -->
                        <div class="mb-2">
                            <div
                                class="relative h-1.5 w-full overflow-hidden rounded-full bg-muted sm:h-2"
                            >
                                <div
                                    class="absolute inset-y-0 left-0 bg-gradient-to-r from-current to-current/70 transition-all duration-500"
                                    :style="{ width: `${progressPercentage}%` }"
                                />
                            </div>
                        </div>

                        <!-- Word metadata -->
                        <div
                            class="flex items-center gap-1 text-xs text-muted-foreground sm:gap-2"
                        >
                            <span>{{ word.frequency }}x</span>
                            <span>·</span>
                            <span>{{ getMasteryLabel(word.mastery_level) }}</span>
                            <template v-if="cardStateLabel">
                                <span>·</span>
                                <span :class="cardStateColor">{{ cardStateLabel }}</span>
                            </template>
                            <span
                                v-if="isDueForReview"
                                class="ml-1 rounded-full bg-primary/10 px-1.5 py-0.5 text-primary"
                            >
                                Due
                            </span>
                            <span
                                v-if="word.review_data?.is_leech"
                                class="ml-1 rounded-full bg-destructive/10 px-1.5 py-0.5 text-destructive"
                            >
                                Leech
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Action buttons (hidden by default, shown on hover) -->
                <div
                    class="absolute top-2 right-2 z-10 opacity-0 transition-opacity duration-200 group-hover:opacity-100"
                >
                    <DropdownMenu>
                        <DropdownMenuTrigger as-child @click.stop>
                            <Button
                                variant="ghost"
                                size="sm"
                                class="h-6 w-6 bg-background/80 p-0 backdrop-blur-sm"
                            >
                                <MoreVertical class="h-3 w-3" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                            <DropdownMenuItem @click.stop="startReview">
                                <BookOpen class="mr-2 h-3 w-3" />
                                Review
                            </DropdownMenuItem>
                            <DropdownMenuItem @click.stop="$emit('edit', word)">
                                <Edit2 class="mr-2 h-3 w-3" />
                                Edit Notes
                            </DropdownMenuItem>
                            <DropdownMenuItem @click.stop="markAsVisited">
                                <Eye class="mr-2 h-3 w-3" />
                                Mark Visited
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                                @click.stop="removeFromList"
                                class="text-destructive"
                            >
                                <Trash2 class="mr-2 h-3 w-3" />
                                Remove
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </ThemedCard>
        </HoverCardTrigger>

        <HoverCardContent class="themed-hovercard w-80" side="bottom" :side-offset="8">
            <div class="space-y-4">
                <!-- Header -->
                <div class="flex items-center justify-between">
                    <div>
                        <h4 class="text-lg font-semibold">
                            {{ word.word?.toLowerCase() ?? '' }}
                        </h4>
                        <p class="text-sm text-muted-foreground">
                            {{ getMasteryLabel(word.mastery_level) }} ·
                            {{
                                word.temperature === Temperature.HOT
                                    ? 'Recently studied'
                                    : 'Not recently studied'
                            }}
                        </p>
                    </div>
                    <div class="text-2xl">
                        {{ getMasteryEmoji(word.mastery_level) }}
                    </div>
                </div>

                <!-- Learning Statistics -->
                <div class="grid grid-cols-2 gap-3">
                    <div class="space-y-1">
                        <div class="text-xs text-muted-foreground">Reviews</div>
                        <div class="font-semibold">
                            {{ word.review_data?.repetitions ?? 0 }}
                        </div>
                    </div>
                    <div class="space-y-1">
                        <div class="text-xs text-muted-foreground">
                            Ease Factor
                        </div>
                        <div class="font-semibold">
                            {{ (word.review_data?.ease_factor ?? 2.5).toFixed(1) }}
                        </div>
                    </div>
                    <div class="space-y-1">
                        <div class="text-xs text-muted-foreground">
                            Interval
                        </div>
                        <div class="font-semibold">
                            {{ formatInterval(word.review_data?.interval ?? 0) }}
                        </div>
                    </div>
                    <div class="space-y-1">
                        <div class="text-xs text-muted-foreground">Lapses</div>
                        <div class="font-semibold">
                            {{ word.review_data?.lapse_count ?? 0 }}
                        </div>
                    </div>
                </div>

                <!-- Timeline -->
                <div class="space-y-2">
                    <div class="text-xs font-medium text-muted-foreground">
                        Timeline
                    </div>
                    <div class="space-y-1 text-xs">
                        <div class="flex justify-between">
                            <span>Added:</span>
                            <span>{{
                                formatRelativeTime(word.added_date)
                            }}</span>
                        </div>
                        <div
                            v-if="word.last_visited"
                            class="flex justify-between"
                        >
                            <span>Last visited:</span>
                            <span>{{
                                formatRelativeTime(word.last_visited)
                            }}</span>
                        </div>
                        <div class="flex justify-between">
                            <span>Next review:</span>
                            <span
                                :class="
                                    isDueForReview
                                        ? 'font-medium text-primary'
                                        : ''
                                "
                            >
                                {{
                                    formatRelativeTime(
                                        word.review_data?.next_review_date
                                    )
                                }}
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Tags -->
                <div v-if="word.tags?.length > 0" class="space-y-2">
                    <div class="text-xs font-medium text-muted-foreground">
                        Tags
                    </div>
                    <div class="flex flex-wrap gap-1">
                        <span
                            v-for="tag in word.tags"
                            :key="tag"
                            class="inline-block rounded-full bg-muted px-2 py-1 text-xs"
                        >
                            {{ tag }}
                        </span>
                    </div>
                </div>

                <!-- Notes -->
                <div v-if="word.notes" class="space-y-2">
                    <div class="text-xs font-medium text-muted-foreground">
                        Notes
                    </div>
                    <div class="rounded-md bg-muted/50 p-2 text-sm">
                        {{ word.notes }}
                    </div>
                </div>

                <!-- Quick actions -->
                <div class="flex gap-2 border-t pt-2">
                    <Button size="sm" @click="startReview" class="flex-1">
                        <BookOpen class="mr-1 h-3 w-3" />
                        Review
                    </Button>
                    <Button
                        size="sm"
                        variant="outline"
                        @click="$emit('edit', word)"
                    >
                        <Edit2 class="mr-1 h-3 w-3" />
                        Edit
                    </Button>
                </div>
            </div>
        </HoverCardContent>
    </HoverCard>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { BookOpen, Edit2, Eye, MoreVertical, Trash2 } from 'lucide-vue-next';
import { ThemedCard } from '@/components/custom/card';
import { Button } from '@/components/ui/button';
import {
    HoverCard,
    HoverCardContent,
    HoverCardTrigger,
} from '@/components/ui/hover-card';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuTrigger,
    DropdownMenuItem,
    DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import type { WordListItem, MasteryLevel, CardState } from '@/types';
import { Temperature } from '@/types';
import { formatRelativeTime } from '@/utils';

interface Props {
    word: WordListItem & { score?: number };
}

const props = defineProps<Props>();

const emit = defineEmits<{
    click: [word: WordListItem];
    review: [word: WordListItem, quality: number];
    edit: [word: WordListItem];
    visited: [word: WordListItem];
    remove: [word: WordListItem];
}>();

/**
 * Format a fractional-day interval into human-readable text.
 * < 1 hour: Xmin, < 1 day: Xhr, >= 1 day: Xd
 */
function formatInterval(days: number): string {
    if (days <= 0) return 'now';
    const minutes = days * 24 * 60;
    if (minutes < 60) return `${Math.round(minutes)}min`;
    const hours = days * 24;
    if (hours < 24) return `${Math.round(hours)}hr`;
    if (days < 365) return `${Math.round(days)}d`;
    const years = days / 365;
    return `${years.toFixed(1)}yr`;
}

// Card state display
const cardStateLabel = computed((): string | null => {
    const state = props.word.review_data?.card_state as CardState | undefined;
    if (!state || state === 'new') return null;
    return {
        learning: 'Learning',
        young: 'Reviewing',
        mature: 'Mature',
        relearning: 'Relearning',
    }[state] ?? null;
});

const cardStateColor = computed(() => {
    const state = props.word.review_data?.card_state as CardState | undefined;
    const colors: Record<string, string> = {
        new: '',
        learning: 'text-blue-500',
        young: 'text-emerald-500',
        mature: 'text-amber-500',
        relearning: 'text-orange-500',
    };
    return colors[state ?? 'new'] ?? '';
});

// Computed properties
const isDueForReview = computed(() => {
    const reviewDate = props.word.review_data?.next_review_date;
    if (!reviewDate) return false;
    return new Date(reviewDate) <= new Date();
});

const progressPercentage = computed(() => {
    const baseProgress = {
        default: 0,
        bronze: 25,
        silver: 60,
        gold: 100,
    }[props.word.mastery_level] ?? 0;

    const reviewBonus = Math.min((props.word.review_data?.repetitions ?? 0) * 2, 20);

    return Math.min(baseProgress + reviewBonus, 100);
});

// Methods
const getMasteryLabel = (level: MasteryLevel): string => {
    return {
        default: 'New',
        bronze: 'Learning',
        silver: 'Familiar',
        gold: 'Mastered',
    }[level] ?? 'New';
};

const getMasteryEmoji = (level: MasteryLevel): string => {
    return {
        default: '📝',
        bronze: '🥉',
        silver: '🥈',
        gold: '🥇',
    }[level] ?? '📝';
};

const startReview = () => {
    emit('review', props.word, 4);
};

const markAsVisited = () => {
    emit('visited', props.word);
};

const removeFromList = () => {
    emit('remove', props.word);
};
</script>

<style scoped>
.themed-title {
    background: linear-gradient(135deg, currentColor 0%, currentColor 100%);
    background-clip: text;
    -webkit-background-clip: text;
}

.themed-hovercard {
    backdrop-filter: blur(20px);
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.2);
}

:root.dark .themed-hovercard {
    background: rgba(0, 0, 0, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.ease-apple-spring {
    transition-timing-function: cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
</style>
