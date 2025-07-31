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
            <div
                v-for="(example, index) in examples"
                :key="example.id || index"
                class="group relative"
            >
                <EditableField
                    :model-value="example.text"
                    field-name="example"
                    :multiline="true"
                    :edit-mode="editMode"
                    :can-regenerate="example.type === 'generated'"
                    :is-regenerating="regeneratingIndex === index"
                    @update:model-value="(val) => updateExample(index, String(val))"
                    @regenerate="() => regenerateExample(index)"
                >
                    <template #display>
                        <p
                            :class="[
                                'text-base leading-relaxed text-foreground italic px-3 py-2 rounded-md border border-border/30 bg-muted/5 transition-all duration-200',
                                editMode ? 'hover:border-border/50 hover:bg-muted/10' : ''
                            ]"
                        >
                            "<span v-html="formatExampleHTML(example.text, word)"></span>"
                            <!-- Type indicator for literature examples -->
                            <span 
                                v-if="example.type === 'literature'" 
                                class="ml-2 text-xs text-muted-foreground/60"
                                title="Literature example"
                            >
                                📚
                            </span>
                        </p>
                    </template>
                </EditableField>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import EditableField from './EditableField.vue';
import { formatExampleHTML } from '../utils/formatting';

import type { Example } from '@/types/api';

interface ExampleListProps {
    examples: Example[];
    word: string;
    editMode: boolean;
}

const props = defineProps<ExampleListProps>();

// Debug logging
console.log('[ExampleListEditable] Examples:', props.examples);

const regeneratingIndex = ref<number | null>(null);

const emit = defineEmits<{
    'update:example': [index: number, value: string];
    'regenerate:example': [index: number];
}>();

function updateExample(index: number, value: string) {
    emit('update:example', index, value);
}

async function regenerateExample(index: number) {
    regeneratingIndex.value = index;
    emit('regenerate:example', index);
    // Parent will handle resetting regeneratingIndex
    setTimeout(() => {
        regeneratingIndex.value = null;
    }, 3000);
}
</script>