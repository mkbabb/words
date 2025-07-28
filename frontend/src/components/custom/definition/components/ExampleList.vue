<template>
    <div
        v-if="examples && examples.length > 0"
        class="mt-8 mb-6"
    >
        <!-- Examples header -->
        <div class="mb-2">
            <span class="text-sm font-medium tracking-wide text-muted-foreground uppercase">
                Examples
            </span>
        </div>

        <div class="space-y-3">
            <p
                v-for="(example, index) in examples"
                :key="example.id || index"
                class="text-base leading-relaxed text-foreground italic px-3 py-2 rounded-md border border-border/30 bg-muted/5 hover:border-border/50 hover:bg-muted/10 transition-all duration-200"
                v-html="`&quot;${formatExampleHTML(example.text, word)}&quot;`"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
import { formatExampleHTML } from '../utils/formatting';

import type { Example } from '@/types/api';

interface ExampleListProps {
    examples: Example[];
    word: string;
    regenerating?: boolean;
}

defineProps<ExampleListProps>();

defineEmits<{
    'regenerate': [];
}>();
</script>