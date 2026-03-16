<template>
    <div v-if="wordlist" class="space-y-4">
        <!-- Stats Cards Row -->
        <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
                <!-- Words -->
                <div class="stat-mastery rounded-xl bg-background/60 dark:bg-white/[0.04] backdrop-blur-sm border border-border/30 p-3">
                    <div class="text-2xl font-bold tabular-nums">{{ wordlist.unique_words }}</div>
                    <div class="text-xs font-medium tracking-wide text-muted-foreground uppercase">Words</div>
                </div>

                <!-- Mastered -->
                <div class="stat-mastery rounded-xl bg-background/60 dark:bg-white/[0.04] backdrop-blur-md border border-border/30 border-mastery-gold bg-mastery-gold p-3">
                    <div class="flex items-baseline gap-1.5">
                        <span class="text-2xl font-bold tabular-nums mastery-gold">{{ mastered }}</span>
                        <span v-if="wordlist.unique_words > 0" class="text-xs text-muted-foreground">
                            / {{ wordlist.unique_words }}
                        </span>
                    </div>
                    <div class="text-xs font-medium tracking-wide mastery-gold opacity-70 uppercase">Mastered</div>
                </div>

                <!-- Due for Review -->
                <div :class="[
                    'stat-mastery rounded-xl bg-background/60 dark:bg-white/[0.04] backdrop-blur-sm border border-border/30 p-3',
                    dueForReview > 0 && 'border-primary/20 bg-primary/5 dark:bg-primary/[0.06]',
                ]">
                    <div :class="[
                        'text-2xl font-bold tabular-nums',
                        dueForReview > 0 ? 'text-primary' : ''
                    ]">{{ dueForReview }}</div>
                    <div :class="[
                        'text-xs font-medium tracking-wide uppercase',
                        dueForReview > 0 ? 'text-primary/70' : 'text-muted-foreground'
                    ]">Due</div>
                </div>

                <!-- Streak -->
                <div :class="[
                    'stat-mastery rounded-xl bg-background/60 dark:bg-white/[0.04] backdrop-blur-sm border border-border/30 p-3',
                    wordlist.learning_stats.streak_days > 0 && 'border-mastery-bronze bg-mastery-bronze',
                ]">
                    <div class="flex items-baseline gap-1">
                        <span :class="[
                            'text-2xl font-bold tabular-nums',
                            wordlist.learning_stats.streak_days > 0 ? 'mastery-bronze' : ''
                        ]">{{ wordlist.learning_stats.streak_days }}</span>
                    </div>
                    <div :class="[
                        'text-xs font-medium tracking-wide uppercase',
                        wordlist.learning_stats.streak_days > 0 ? 'mastery-bronze opacity-70' : 'text-muted-foreground'
                    ]">Streak</div>
                </div>
            </div>

        <!-- Divider -->
        <div class="border-b border-border/50" />
    </div>
</template>

<script setup lang="ts">
import type { WordList } from '@/types';

defineProps<{
    wordlist: WordList | null;
    mastered: number;
    dueForReview: number;
}>();
</script>
