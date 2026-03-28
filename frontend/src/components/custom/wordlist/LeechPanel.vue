<script setup lang="ts">
import { computed, ref } from 'vue';
import { Skull, Ban, Play } from 'lucide-vue-next';
import { api } from '@/api/core';
import type { WordListItem } from '@/types';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@mkbabb/glass-ui';

const props = defineProps<{
    wordlistId: string;
    words: WordListItem[];
}>();

const emit = defineEmits<{
    refresh: [];
}>();

const leechWords = computed(() =>
    props.words.filter((w) => w.review_data?.is_leech)
);

const processing = ref<string | null>(null);

async function suspendLeech(word: string) {
    processing.value = word;
    try {
        await api.post(
            `/wordlists/${props.wordlistId}/review/leeches/${encodeURIComponent(word)}/suspend`
        );
        emit('refresh');
    } catch {
        // silent fail
    } finally {
        processing.value = null;
    }
}

async function unsuspendLeech(word: string) {
    processing.value = word;
    try {
        await api.post(
            `/wordlists/${props.wordlistId}/review/leeches/${encodeURIComponent(word)}/unsuspend`
        );
        emit('refresh');
    } catch {
        // silent fail
    } finally {
        processing.value = null;
    }
}
</script>

<template>
    <div class="space-y-3">
        <div class="flex items-center gap-2 text-sm font-medium text-destructive">
            <Skull class="w-4 h-4" />
            <span>Leech Words ({{ leechWords.length }})</span>
        </div>

        <div
            v-if="leechWords.length === 0"
            class="text-sm text-muted-foreground py-4 text-center"
        >
            No leech words — great job!
        </div>

        <div v-else class="space-y-2">
            <div
                v-for="item in leechWords"
                :key="item.word"
                class="flex items-center justify-between rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 transition-colors duration-200 hover:bg-accent/50"
            >
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium truncate">{{ item.word }}</p>
                    <div class="flex gap-3 text-xs text-muted-foreground mt-0.5">
                        <span>Lapses: {{ item.review_data.lapse_count }}</span>
                        <span
                            >Ease:
                            {{ item.review_data.ease_factor.toFixed(2) }}</span
                        >
                        <span>Interval: {{ item.review_data.interval }}d</span>
                    </div>
                </div>

                <div class="flex items-center gap-1">
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger as-child>
                                <button
                                    class="p-1.5 rounded-md hover:bg-destructive/10 text-destructive/60 hover:text-destructive transition-colors"
                                    :disabled="processing === item.word"
                                    @click="suspendLeech(item.word)"
                                >
                                    <Ban class="w-3.5 h-3.5" />
                                </button>
                            </TooltipTrigger>
                            <TooltipContent
                                >Suspend from reviews</TooltipContent
                            >
                        </Tooltip>
                    </TooltipProvider>

                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger as-child>
                                <button
                                    class="p-1.5 rounded-md hover:bg-primary/10 text-muted-foreground hover:text-primary transition-colors"
                                    :disabled="processing === item.word"
                                    @click="unsuspendLeech(item.word)"
                                >
                                    <Play class="w-3.5 h-3.5" />
                                </button>
                            </TooltipTrigger>
                            <TooltipContent>Resume reviews</TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                </div>
            </div>
        </div>
    </div>
</template>
