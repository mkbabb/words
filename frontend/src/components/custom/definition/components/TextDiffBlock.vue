<template>
    <div
        class="rounded-lg border border-border/20 bg-muted/5 px-3 py-2 text-sm"
    >
        <div class="mb-1.5 font-mono text-[10px] font-medium text-muted-foreground/50">
            {{ label }}
        </div>
        <InlineDiff :old-text="oldText" :new-text="newText" />
    </div>
</template>

<script setup lang="ts">
import InlineDiff from './InlineDiff.vue';

interface Props {
    label: string;
    oldText: string;
    newText: string;
}

defineProps<Props>();
</script>
