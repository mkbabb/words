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
            <!-- Part of Speech with Progressive Loading -->
            <div v-if="definition.part_of_speech">
                <EditableField
                    v-model="fields.part_of_speech.value"
                    field-name="part of speech"
                    :edit-mode="props.editModeEnabled"
                    :errors="fields.part_of_speech.errors"
                    @update:model-value="(value) => { 
                        fields.part_of_speech.value = String(value);
                        fields.part_of_speech.isDirty = true;
                        save(); 
                    }"
                >
                    <template #display>
                        <span class="text-2xl font-semibold text-primary">
                            {{ definition.part_of_speech }}
                        </span>
                    </template>
                </EditableField>
            </div>
            <!-- Part of Speech Skeleton -->
            <div v-else-if="isStreaming" class="h-8 w-20 bg-muted rounded animate-pulse" />
            
            <sup class="text-sm font-normal text-muted-foreground">{{ definitionIndex + 1 }}</sup>
            
            <!-- Streaming Indicator -->
            <div v-if="isStreaming && isPartialDefinition" class="flex items-center gap-1 ml-2">
                <div class="h-1.5 w-1.5 bg-blue-500 rounded-full animate-pulse" />
                <span class="text-xs text-blue-500">loading...</span>
            </div>
            
        </div>

        <div class="border-l-2 border-accent pl-4">
            <!-- Definition Text with Progressive Loading -->
            <div v-if="definition.text">
                <EditableField
                    v-model="fields.text.value"
                    field-name="definition"
                    :multiline="true"
                    :edit-mode="props.editModeEnabled"
                    :can-regenerate="canRegenerate('text')"
                :is-regenerating="fields.text.isRegenerating"
                :errors="fields.text.errors"
                @regenerate="regenerateComponent('text')"
                @update:model-value="(val: string | number | string[]) => { 
                    fields.text.value = String(val);
                    fields.text.isDirty = true;
                    save(); 
                }"
            >
                <template #display>
                    <p class="text-base leading-relaxed" style="font-family: 'Fraunces', serif;">
                        {{ definition.definition || definition.text }}
                    </p>
                </template>
                </EditableField>
            </div>
            <!-- Definition Text Skeleton -->
            <div v-else-if="isStreaming" class="space-y-2 animate-pulse">
                <div class="h-6 w-full bg-muted rounded" />
                <div class="h-4 w-4/5 bg-muted rounded" />
            </div>

            <!-- Progressive Examples -->
            <ExampleListEditable
                v-if="definition.examples && definition.examples.length > 0"
                :examples="definition.examples"
                :word="store.currentEntry?.word || ''"
                :edit-mode="props.editModeEnabled"
                :isStreaming="isStreaming"
                @update:example="handleExampleUpdate"
                @regenerate:example="handleExampleRegenerate"
            />
            <!-- Examples Skeleton -->
            <div v-else-if="isStreaming || isPartialDefinition" class="mt-4 space-y-2">
                <div class="text-sm font-medium text-muted-foreground">Examples</div>
                <div v-for="i in 2" :key="i" class="bg-muted/50 rounded p-3 animate-pulse">
                    <div class="h-4 w-full bg-muted rounded mb-1" />
                    <div class="h-4 w-3/4 bg-muted rounded" />
                </div>
            </div>

            <!-- Progressive Synonyms -->
            <SynonymListEditable
                v-if="shouldShowSynonyms"
                :synonyms="fields.synonyms.value"
                :edit-mode="props.editModeEnabled"
                :can-regenerate="canRegenerate('synonyms')"
                :is-regenerating="fields.synonyms.isRegenerating"
                @update:synonyms="(val) => { fields.synonyms.value = val; save(); }"
                @regenerate="regenerateComponent('synonyms')"
                @synonym-click="emit('searchWord', $event)"
            />
            <!-- Synonyms Skeleton -->
            <div v-else-if="isStreaming || isPartialDefinition" class="mt-4 space-y-2">
                <div class="text-sm font-medium text-muted-foreground">Synonyms</div>
                <div class="flex flex-wrap gap-1">
                    <div v-for="i in 4" :key="i" class="h-6 w-16 bg-muted rounded animate-pulse" />
                </div>
            </div>
        </div>
    </div>
</template>


<script setup lang="ts">
import { computed } from 'vue';
import { useAppStore } from '@/stores';
import { useDefinitionEditMode } from '@/composables';
import type { TransformedDefinition } from '@/types';
import ExampleListEditable from './ExampleListEditable.vue';
import SynonymListEditable from './SynonymListEditable.vue';
import EditableField from './EditableField.vue';

interface DefinitionItemProps {
    definition: TransformedDefinition;
    definitionIndex: number;
    isRegenerating: boolean;
    isFirstInGroup?: boolean;
    isAISynthesized?: boolean;
    editModeEnabled?: boolean;
    isStreaming?: boolean;
}

const store = useAppStore();
const props = defineProps<DefinitionItemProps>();

// Streaming indicators
const isStreaming = computed(() => props.isStreaming || false);
const isPartialDefinition = computed(() => {
    return isStreaming.value && (!props.definition.text || !props.definition.examples?.length);
});

// Debug logging
console.log('[DefinitionItem] Definition:', props.definition);
console.log('[DefinitionItem] Definition ID:', props.definition.id);
console.log('[DefinitionItem] Definition examples:', props.definition.examples);

// Create a ref for the definition to use with edit mode
const definitionRef = computed(() => props.definition);

// Use edit mode composable
const {
    fields,
    save,
    regenerateComponent,
    canRegenerate,
} = useDefinitionEditMode(definitionRef, {
    onSave: async (updates) => {
        console.log('[DefinitionItem] onSave called with updates:', updates);
        if (props.definition.id) {
            console.log('[DefinitionItem] Calling store.updateDefinition with id:', props.definition.id);
            await store.updateDefinition(props.definition.id, updates);
        } else {
            console.error('[DefinitionItem] No definition ID available!');
        }
    },
    onRegenerate: async (component) => {
        if (props.definition.id) {
            await store.regenerateDefinitionComponent(props.definition.id, component);
        }
    },
});

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

const emit = defineEmits<{
    'regenerate': [index: number];
    'searchWord': [word: string];
    'addToWordlist': [word: string];
}>();


// Handle example updates
async function handleExampleUpdate(index: number, value: string) {
    console.log('[DefinitionItem] handleExampleUpdate:', index, value);
    if (props.definition.examples && props.definition.examples[index]) {
        const example = props.definition.examples[index];
        if (example.id) {
            console.log('[DefinitionItem] Updating example with ID:', example.id);
            try {
                // Update via the examples API endpoint
                await store.updateExample(example.id, { text: value });
                // Update local state after successful save
                example.text = value;
            } catch (error) {
                console.error('[DefinitionItem] Failed to update example:', error);
                store.showNotification({
                    type: 'error',
                    message: 'Failed to update example',
                    duration: 3000
                });
            }
        } else {
            console.warn('[DefinitionItem] Example has no ID, cannot update');
        }
    }
}

// Handle individual example regeneration
async function handleExampleRegenerate(index: number) {
    if (props.definition.examples && props.definition.examples[index]?.type === 'generated' && props.definition.id) {
        // Call store method to regenerate single example
        emit('regenerate', props.definitionIndex);
    }
}
</script>