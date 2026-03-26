<template>
    <div v-if="wordlist" class="space-y-4">
        <!-- Stats Row — no background cards, just numbers -->
        <div class="flex items-end gap-8 flex-wrap">
            <!-- Words -->
            <div>
                <p class="text-3xl font-bold tabular-nums font-serif leading-none">{{ formatCount(wordlist.unique_words) }}</p>
                <p class="mt-1 text-xs text-muted-foreground/60 uppercase tracking-widest">Words</p>
            </div>

            <!-- Mastered -->
            <div>
                <div class="flex items-baseline gap-1.5">
                    <p class="text-3xl font-bold tabular-nums font-serif leading-none mastery-gold">{{ formatCount(mastered) }}</p>
                    <span v-if="wordlist.unique_words > 0" class="text-sm text-muted-foreground/40 tabular-nums">
                        / {{ formatCount(wordlist.unique_words) }}
                    </span>
                </div>
                <p class="mt-1 text-xs mastery-gold opacity-60 uppercase tracking-widest">Mastered</p>
            </div>

            <!-- Due for Review -->
            <div>
                <p :class="[
                    'text-3xl font-bold tabular-nums font-serif leading-none',
                    dueForReview > 0 ? 'text-primary' : ''
                ]">{{ formatCount(dueForReview) }}</p>
                <p :class="[
                    'mt-1 text-xs uppercase tracking-widest',
                    dueForReview > 0 ? 'text-primary/60' : 'text-muted-foreground/60'
                ]">Due</p>
            </div>

            <!-- Streak -->
            <div v-if="wordlist.learning_stats.streak_days > 0">
                <p class="text-3xl font-bold tabular-nums font-serif leading-none mastery-bronze flex items-end gap-1">
                    <Flame class="h-6 w-6 mb-0.5" />
                    {{ formatCount(wordlist.learning_stats.streak_days) }}
                </p>
                <p class="mt-1 text-xs mastery-bronze opacity-60 uppercase tracking-widest">Streak</p>
            </div>
        </div>

        <!-- Divider -->
        <div class="border-b border-border/50" />
    </div>
</template>

<script setup lang="ts">
import { Flame } from 'lucide-vue-next';
import type { WordList } from '@/types';
import { formatCount } from './utils/formatting';

defineProps<{
    wordlist: WordList | null;
    mastered: number;
    dueForReview: number;
}>();
</script>
