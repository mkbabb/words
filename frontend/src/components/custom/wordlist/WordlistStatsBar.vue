<template>
    <div v-if="wordlist" class="space-y-4">
        <!-- Stats Cards Row -->
        <div class="flex items-center gap-3">
            <div class="grid flex-1 grid-cols-2 gap-3 md:grid-cols-4">
                <!-- Words -->
                <div class="stat-card rounded-xl border border-border/40 bg-background/60 p-3 backdrop-blur-sm">
                    <div class="text-2xl font-bold tabular-nums">{{ wordlist.unique_words }}</div>
                    <div class="text-xs font-medium tracking-wide text-muted-foreground uppercase">Words</div>
                </div>

                <!-- Mastered -->
                <div class="stat-card rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 backdrop-blur-sm">
                    <div class="flex items-baseline gap-1.5">
                        <span class="text-2xl font-bold tabular-nums text-amber-600 dark:text-amber-400">{{ mastered }}</span>
                        <span v-if="wordlist.unique_words > 0" class="text-xs text-muted-foreground">
                            / {{ wordlist.unique_words }}
                        </span>
                    </div>
                    <div class="text-xs font-medium tracking-wide text-amber-600/70 dark:text-amber-400/70 uppercase">Mastered</div>
                </div>

                <!-- Due for Review -->
                <div :class="[
                    'stat-card rounded-xl border p-3 backdrop-blur-sm',
                    dueForReview > 0
                        ? 'border-primary/20 bg-primary/5'
                        : 'border-border/40 bg-background/60'
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
                    'stat-card rounded-xl border p-3 backdrop-blur-sm',
                    wordlist.learning_stats.streak_days > 0
                        ? 'border-orange-500/20 bg-orange-500/5'
                        : 'border-border/40 bg-background/60'
                ]">
                    <div class="flex items-baseline gap-1">
                        <span :class="[
                            'text-2xl font-bold tabular-nums',
                            wordlist.learning_stats.streak_days > 0 ? 'text-orange-500' : ''
                        ]">{{ wordlist.learning_stats.streak_days }}</span>
                        <span v-if="wordlist.learning_stats.streak_days > 0" class="text-sm">🔥</span>
                    </div>
                    <div :class="[
                        'text-xs font-medium tracking-wide uppercase',
                        wordlist.learning_stats.streak_days > 0 ? 'text-orange-500/70' : 'text-muted-foreground'
                    ]">Streak</div>
                </div>
            </div>

            <!-- Actions slot (Review button etc) -->
            <div class="shrink-0">
                <slot name="actions" />
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

<style scoped>
.stat-card {
    transition: all 0.2s ease;
}
.stat-card:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}
</style>
