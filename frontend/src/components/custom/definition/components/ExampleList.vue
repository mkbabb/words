<template>
    <div
        v-if="examples && (examples.generated.length > 0 || examples.literature.length > 0)"
        class="mt-8 mb-6"
    >
        <!-- Examples header with regenerate button -->
        <div class="mb-2 flex items-center justify-between">
            <span class="text-sm font-medium tracking-wide text-muted-foreground uppercase">
                Examples
            </span>
            <button
                v-if="examples.generated.length > 0"
                @click="$emit('regenerate')"
                :class="[
                    'group flex items-center gap-1 rounded-md px-2 py-1',
                    'text-sm transition-all duration-200',
                    'hover:bg-primary/10',
                    regenerating ? 'text-primary' : 'text-muted-foreground hover:text-primary',
                ]"
                :disabled="regenerating"
                title="Regenerate examples"
            >
                <RefreshCw
                    :size="12"
                    :class="[
                        'transition-transform duration-300',
                        'group-hover:rotate-180',
                        regenerating && 'animate-spin',
                    ]"
                />
            </button>
        </div>

        <div class="space-y-3">
            <p
                v-for="(example, index) in [...examples.generated, ...examples.literature]"
                :key="index"
                class="text-base leading-relaxed text-foreground italic px-3 py-2 rounded-md border border-border/30 bg-muted/5 hover:border-border/50 hover:bg-muted/10 transition-all duration-200"
                v-html="`&quot;${formatExampleHTML(example.sentence, word)}&quot;`"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
import { RefreshCw } from 'lucide-vue-next';
import { formatExampleHTML } from '../utils/formatting';

interface Example {
    sentence: string;
    regenerable?: boolean;
    source?: string;
}

interface ExampleListProps {
    examples: {
        generated: Example[];
        literature: Example[];
    };
    word: string;
    regenerating: boolean;
}

defineProps<ExampleListProps>();

defineEmits<{
    'regenerate': [];
}>();
</script>