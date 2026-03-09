<template>
    <span v-if="isFullReplacement" class="inline-diff">
        <span
            class="block rounded-sm bg-red-500/15 px-1 py-0.5 text-red-600 line-through decoration-red-400/60 dark:bg-red-500/10 dark:text-red-400"
            >{{ segments[0].text }}</span
        >
        <span
            class="mt-1 block rounded-sm bg-emerald-500/15 px-1 py-0.5 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
            >{{ segments[1].text }}</span
        >
    </span>
    <span v-else class="inline-diff">
        <template v-for="(seg, i) in segments" :key="i">
            <span
                v-if="seg.type === 'removed'"
                class="rounded-sm bg-red-500/15 px-0.5 text-red-600 line-through decoration-red-400/60 dark:bg-red-500/10 dark:text-red-400"
                >{{ seg.text }}</span
            >
            <span
                v-else-if="seg.type === 'added'"
                class="rounded-sm bg-emerald-500/15 px-0.5 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400"
                >{{ seg.text }}</span
            >
            <span v-else>{{ seg.text }}</span>
        </template>
    </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { wordDiff, type DiffSegment } from '@/utils/wordDiff';

interface Props {
    oldText: string;
    newText: string;
}

const props = defineProps<Props>();

const segments = computed((): DiffSegment[] => {
    return wordDiff(props.oldText ?? '', props.newText ?? '');
});

/** True when the diff is a clean full-replacement (old block → new block). */
const isFullReplacement = computed(() => {
    const s = segments.value;
    return (
        s.length === 2 &&
        s[0].type === 'removed' &&
        s[1].type === 'added'
    );
});
</script>
