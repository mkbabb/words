<template>
    <div v-if="wordlist" class="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div class="rounded-lg bg-muted/30 p-3">
            <div class="text-2xl font-bold">{{ wordlist.unique_words }}</div>
            <div class="text-sm text-muted-foreground">Words</div>
        </div>
        <div class="rounded-lg bg-muted/30 p-3">
            <div class="text-2xl font-bold">{{ mastered }}</div>
            <div class="text-sm text-muted-foreground">Mastered</div>
        </div>
        <div class="rounded-lg bg-muted/30 p-3">
            <div class="text-2xl font-bold">{{ dueForReview }}</div>
            <div class="text-sm text-muted-foreground">Due</div>
        </div>
        <div class="rounded-lg bg-muted/30 p-3">
            <div class="text-2xl font-bold">
                {{ wordlist.learning_stats.streak_days }}
            </div>
            <div class="text-sm text-muted-foreground">Day Streak</div>
        </div>
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
