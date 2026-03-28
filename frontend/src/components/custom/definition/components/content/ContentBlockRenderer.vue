<script setup lang="ts">
import { inject } from 'vue';
import { PAPER_CONTEXT, MathBlock, CodeBlock } from '@mkbabb/latex-paper/vue';
import type { ContentBlock } from '@mkbabb/latex-paper';

defineProps<{
    blocks: ContentBlock[];
}>();

const ctx = inject(PAPER_CONTEXT)!;

function renderParagraph(text: string): string {
    // renderTitle replaces $...$ with KaTeX HTML inline
    return ctx.renderTitle(text);
}
</script>

<template>
    <template v-for="(block, i) in blocks" :key="i">
        <!-- Paragraph (with inline math via renderTitle) -->
        <span v-if="typeof block === 'string'" v-html="renderParagraph(block)" />

        <!-- Display math -->
        <MathBlock
            v-else-if="'tex' in block"
            :tex="(block as any).tex"
            :id="(block as any).id"
            :number="(block as any).number"
            :numbered="(block as any).numbered"
        />

        <!-- Code block -->
        <CodeBlock
            v-else-if="'code' in block"
            :code="(block as any).code.code"
            :caption="(block as any).code.caption"
            :language="(block as any).code.language"
        />
    </template>
</template>
