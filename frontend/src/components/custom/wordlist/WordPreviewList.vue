<template>
    <div v-if="parsedWords.length > 0" class="space-y-3">
        <div class="flex items-center justify-between">
            <h3 class="font-medium">Words Found ({{ parsedWords.length }})</h3>
            <Button @click="showAll = !showAll" variant="ghost" size="sm">
                {{ showAll ? 'Show Less' : 'Show All' }}
            </Button>
        </div>

        <div class="max-h-40 overflow-y-auto rounded-md bg-muted/30 p-3">
            <div class="grid grid-cols-1 gap-1">
                <div
                    v-for="(word, index) in displayedWords"
                    :key="index"
                    class="flex items-center justify-between py-1"
                >
                    <span class="text-sm">{{ word.text }}</span>
                    <div
                        class="flex items-center gap-2 text-xs text-muted-foreground"
                    >
                        <span v-if="word.frequency > 1"
                            >{{ word.frequency }}x</span
                        >
                        <span v-if="word.notes" class="rounded bg-muted px-1">
                            {{ word.notes }}
                        </span>
                    </div>
                </div>
            </div>

            <div
                v-if="!showAll && parsedWords.length > 10"
                class="pt-2 text-center"
            >
                <span class="text-xs text-muted-foreground">
                    ... and {{ parsedWords.length - 10 }} more
                </span>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { Button } from '@/components/ui/button';
import type { ParsedWord } from './composables/useWordlistFileParser';

const props = defineProps<{
    parsedWords: ParsedWord[];
}>();

const showAll = ref(false);

const displayedWords = computed(() => {
    return showAll.value ? props.parsedWords : props.parsedWords.slice(0, 10);
});
</script>
