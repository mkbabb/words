<template>
    <div
        :id="`def-${definitionIndex}`"
        :data-definition-index="definitionIndex"
        :data-part-of-speech="`${definition.meaning_cluster?.id || 'default'}-${definition.part_of_speech}`"
        class="space-y-2"
    >
        <!-- Separator for definitions within same cluster -->
        <hr
            v-if="isSeparatorNeeded"
            class="my-2 border-border/50"
        />

        <div class="flex items-center gap-2">
            <span class="text-2xl font-semibold text-primary">
                {{ definition.part_of_speech }}
            </span>
            <sup class="text-sm font-normal text-muted-foreground">{{ definitionIndex + 1 }}</sup>
        </div>

        <div class="border-l-2 border-accent pl-4">
            <p class="text-base leading-relaxed" style="font-family: 'Fraunces', serif;">
                {{ definition.definition || definition.text }}
            </p>

            <!-- Examples -->
            <ExampleList
                v-if="definition.examples"
                :examples="definition.examples"
                :word="store.currentEntry?.word || ''"
                :regenerating="isRegenerating"
                @regenerate="$emit('regenerate', definitionIndex)"
            />

            <!-- Synonyms -->
            <SynonymList
                v-if="shouldShowSynonyms"
                :synonyms="definition.synonyms"
                @synonym-click="$emit('searchWord', $event)"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAppStore } from '@/stores';
import type { TransformedDefinition } from '@/types';
import ExampleList from './ExampleList.vue';
import SynonymList from './SynonymList.vue';

interface DefinitionItemProps {
    definition: TransformedDefinition;
    definitionIndex: number;
    isRegenerating: boolean;
    isFirstInGroup?: boolean;
    isAISynthesized?: boolean;
}

const store = useAppStore();
const props = defineProps<DefinitionItemProps>();

// Check if we need separator (not the first definition in the overall list)
const isSeparatorNeeded = computed(() => props.definitionIndex > 0);

// For non-AI entries, only show synonyms on the first definition to avoid repetition
const shouldShowSynonyms = computed(() => {
    if (props.isAISynthesized !== false) {
        // For AI entries or undefined, always show synonyms
        return props.definition.synonyms && props.definition.synonyms.length > 0;
    }
    // For non-AI entries, only show on first definition
    return props.isFirstInGroup && props.definition.synonyms && props.definition.synonyms.length > 0;
});

defineEmits<{
    'regenerate': [index: number];
    'searchWord': [word: string];
}>();
</script>