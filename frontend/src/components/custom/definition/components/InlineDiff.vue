<template>
    <span v-if="isFullReplacement" class="inline-diff">
        <span
            class="block rounded-sm bg-destructive/15 px-1 py-0.5 text-destructive line-through decoration-destructive/60"
            >{{ segments[0].text }}</span
        >
        <span
            class="mt-1 block rounded-sm bg-[var(--color-success)]/15 px-1 py-0.5 text-[var(--color-success)]"
            >{{ segments[1].text }}</span
        >
    </span>
    <span v-else class="inline-diff">
        <template v-for="(seg, i) in segments" :key="i">
            <span
                v-if="seg.type === 'removed'"
                class="rounded-sm bg-destructive/15 px-0.5 text-destructive line-through decoration-destructive/60"
                >{{ seg.text }}</span
            >
            <span
                v-else-if="seg.type === 'added'"
                class="rounded-sm bg-[var(--color-success)]/15 px-0.5 text-[var(--color-success)]"
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
