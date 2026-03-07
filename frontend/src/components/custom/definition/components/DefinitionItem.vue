<template>
    <div
        :id="`def-${definitionIndex}`"
        :data-definition-index="definitionIndex"
        :data-part-of-speech="`${definition.meaning_cluster?.id || 'default'}-${definition.part_of_speech}`"
        class="space-y-2"
    >
        <!-- Separator for definitions within same cluster -->
        <hr v-if="isSeparatorNeeded" class="my-2 border-border/50" />

        <div class="flex items-center gap-2">
            <!-- Part of Speech with Progressive Loading -->
            <div v-if="definition.part_of_speech">
                <EditableField
                    v-model="fields.part_of_speech.value"
                    field-name="part of speech"
                    :edit-mode="props.editModeEnabled"
                    :errors="fields.part_of_speech.errors"
                    @update:model-value="
                        (value) => {
                            fields.part_of_speech.value = String(value);
                            fields.part_of_speech.isDirty = true;
                            save();
                        }
                    "
                >
                    <template #display>
                        <span class="text-2xl font-semibold text-primary">
                            {{ definition.part_of_speech }}
                        </span>
                    </template>
                </EditableField>
            </div>
            <!-- Part of Speech Skeleton -->
            <div
                v-else-if="isStreaming"
                class="h-8 w-20 animate-pulse rounded bg-muted"
            />

            <sup class="text-sm font-normal text-muted-foreground">{{
                definitionIndex + 1
            }}</sup>

            <!-- Streaming Indicator -->
            <div
                v-if="isStreaming && isPartialDefinition"
                class="ml-2 flex items-center gap-1"
            >
                <div
                    class="h-1.5 w-1.5 animate-pulse rounded-full bg-blue-500"
                />
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
                    @update:model-value="
                        (val: string | number | string[]) => {
                            fields.text.value = String(val);
                            fields.text.isDirty = true;
                            save();
                        }
                    "
                >
                    <template #display>
                        <p
                            class="text-base leading-relaxed font-serif"
                        >
                            {{ definition.definition || definition.text }}
                        </p>
                    </template>
                </EditableField>
            </div>
            <!-- Definition Text Skeleton -->
            <div v-else-if="isStreaming" class="animate-pulse space-y-2">
                <div class="h-6 w-full rounded bg-muted" />
                <div class="h-4 w-4/5 rounded bg-muted" />
            </div>

            <!-- Source Attribution Labels (admin edit mode) -->
            <div
                v-if="editModeEnabled && definition.source_definitions?.length"
                class="mt-1 flex flex-wrap gap-1"
            >
                <span
                    v-for="src in definition.source_definitions"
                    :key="src.entry_id"
                    class="inline-flex items-center rounded border border-border/50 bg-muted/30 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground"
                >
                    {{ getProviderDisplayName(src.provider) }}
                    <span v-if="src.entry_version" class="ml-0.5 opacity-60">v{{ src.entry_version }}</span>
                </span>
            </div>

            <!-- Progressive Examples -->
            <ExampleListEditable
                v-if="definition.examples && definition.examples.length > 0"
                :examples="definition.examples"
                :word="props.word || contentStore.currentEntry?.word || ''"
                :edit-mode="props.editModeEnabled"
                :isStreaming="isStreaming"
                @update:example="handleExampleUpdate"
                @regenerate:example="handleExampleRegenerate"
            />
            <!-- Examples Skeleton -->
            <div
                v-else-if="isStreaming || isPartialDefinition"
                class="mt-4 space-y-2"
            >
                <div class="text-sm font-medium text-muted-foreground">
                    Examples
                </div>
                <div
                    v-for="i in 2"
                    :key="i"
                    class="animate-pulse rounded bg-muted/50 p-3"
                >
                    <div class="mb-1 h-4 w-full rounded bg-muted" />
                    <div class="h-4 w-3/4 rounded bg-muted" />
                </div>
            </div>

            <!-- Progressive Synonyms -->
            <SynonymListEditable
                v-if="shouldShowSynonyms"
                :synonyms="fields.synonyms.value"
                :edit-mode="props.editModeEnabled"
                :can-regenerate="canRegenerate('synonyms')"
                :is-regenerating="fields.synonyms.isRegenerating"
                @update:synonyms="
                    (val) => {
                        fields.synonyms.value = val;
                        save();
                    }
                "
                @regenerate="regenerateComponent('synonyms')"
                @synonym-click="emit('searchWord', $event)"
            />
            <!-- Synonyms Skeleton -->
            <div
                v-else-if="isStreaming || isPartialDefinition"
                class="mt-4 space-y-2"
            >
                <div class="text-sm font-medium text-muted-foreground">
                    Synonyms
                </div>
                <div class="flex flex-wrap gap-1">
                    <div
                        v-for="i in 4"
                        :key="i"
                        class="h-6 w-16 animate-pulse rounded bg-muted"
                    />
                </div>
            </div>

            <!-- Antonyms (reuses SynonymListEditable pattern) -->
            <SynonymListEditable
                v-if="editModeEnabled && definition.antonyms && definition.antonyms.length > 0"
                :synonyms="fields.antonyms.value"
                :edit-mode="editModeEnabled"
                :can-regenerate="canRegenerate('antonyms')"
                :is-regenerating="fields.antonyms.isRegenerating"
                @update:synonyms="
                    (val) => {
                        fields.antonyms.value = val;
                        save();
                    }
                "
                @regenerate="regenerateComponent('antonyms')"
                @synonym-click="emit('searchWord', $event)"
            />

            <!-- Domain, Region, Frequency (edit mode only) -->
            <div v-if="editModeEnabled" class="mt-3 flex flex-wrap gap-3">
                <EditableField
                    v-if="definition.domain || editModeEnabled"
                    v-model="fields.domain.value"
                    field-name="domain"
                    :edit-mode="editModeEnabled"
                    :can-regenerate="canRegenerate('domain')"
                    :is-regenerating="fields.domain.isRegenerating"
                    @regenerate="regenerateComponent('domain')"
                    @update:model-value="
                        (val) => {
                            fields.domain.value = String(val || '');
                            fields.domain.isDirty = true;
                            save();
                        }
                    "
                >
                    <template #display>
                        <span v-if="definition.domain" class="text-xs text-muted-foreground">
                            Domain: {{ definition.domain }}
                        </span>
                    </template>
                </EditableField>

                <EditableField
                    v-if="definition.region || editModeEnabled"
                    v-model="fields.region.value"
                    field-name="region"
                    :edit-mode="editModeEnabled"
                    @update:model-value="
                        (val) => {
                            fields.region.value = String(val || '');
                            fields.region.isDirty = true;
                            save();
                        }
                    "
                >
                    <template #display>
                        <span v-if="definition.region" class="text-xs text-muted-foreground">
                            Region: {{ definition.region }}
                        </span>
                    </template>
                </EditableField>

                <div v-if="definition.frequency_band || editModeEnabled" class="flex items-center gap-1">
                    <span class="text-xs text-muted-foreground">Freq:</span>
                    <div class="flex gap-0.5">
                        <button
                            v-for="star in 5"
                            :key="star"
                            @click="
                                fields.frequency_band.value = star;
                                fields.frequency_band.isDirty = true;
                                save();
                            "
                            class="text-xs transition-colors"
                            :class="star <= (fields.frequency_band.value || 0) ? 'text-yellow-500' : 'text-muted-foreground/30'"
                        >
                            &#9733;
                        </button>
                    </div>
                </div>
            </div>

            <!-- Usage Notes (edit mode) -->
            <div v-if="editModeEnabled && definition.usage_notes?.length" class="mt-3 space-y-1">
                <div class="text-xs font-medium text-muted-foreground">Usage Notes</div>
                <div
                    v-for="(note, i) in definition.usage_notes"
                    :key="i"
                    class="rounded border border-border/50 bg-muted/20 px-2 py-1 text-xs"
                >
                    <span class="font-medium text-muted-foreground">{{ note.type }}:</span>
                    {{ note.text }}
                </div>
            </div>

            <!-- Grammar Patterns (edit mode) -->
            <div v-if="editModeEnabled && definition.grammar_patterns?.length" class="mt-3 space-y-1">
                <div class="text-xs font-medium text-muted-foreground">Grammar Patterns</div>
                <div
                    v-for="(pattern, i) in definition.grammar_patterns"
                    :key="i"
                    class="rounded border border-border/50 bg-muted/20 px-2 py-1 text-xs font-mono"
                >
                    {{ pattern.pattern }}
                    <span v-if="pattern.description" class="ml-1 font-sans text-muted-foreground">
                        — {{ pattern.description }}
                    </span>
                </div>
            </div>

            <!-- Collocations (edit mode) -->
            <div v-if="editModeEnabled && definition.collocations?.length" class="mt-3">
                <div class="text-xs font-medium text-muted-foreground mb-1">Collocations</div>
                <div class="flex flex-wrap gap-1">
                    <span
                        v-for="(coll, i) in definition.collocations"
                        :key="i"
                        class="rounded border border-border/50 bg-muted/30 px-1.5 py-0.5 text-xs"
                    >
                        {{ coll.text }}
                        <span class="text-muted-foreground/60">{{ coll.type }}</span>
                    </span>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useContentStore, useNotificationStore } from '@/stores';
import { useDefinitionEditMode } from '../composables';
import type { TransformedDefinition } from '@/types';
import ExampleListEditable from './ExampleListEditable.vue';
import SynonymListEditable from './SynonymListEditable.vue';
import EditableField from './EditableField.vue';
import { DictionaryProvider } from '@/types/api';
import { logger } from '@/utils/logger';

const PROVIDER_DISPLAY_NAMES: Record<string, string> = {
    [DictionaryProvider.WIKTIONARY]: 'Wiktionary',
    [DictionaryProvider.OXFORD]: 'Oxford',
    [DictionaryProvider.APPLE_DICTIONARY]: 'Apple Dict',
    [DictionaryProvider.MERRIAM_WEBSTER]: 'Merriam-Webster',
    [DictionaryProvider.FREE_DICTIONARY]: 'Free Dict',
    [DictionaryProvider.WORDHIPPO]: 'WordHippo',
    [DictionaryProvider.AI_FALLBACK]: 'AI Fallback',
    [DictionaryProvider.SYNTHESIS]: 'Synthesis',
};

function getProviderDisplayName(provider: string): string {
    return PROVIDER_DISPLAY_NAMES[provider] || provider.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

interface DefinitionItemProps {
    definition: TransformedDefinition;
    definitionIndex: number;
    isRegenerating: boolean;
    isFirstInGroup?: boolean;
    isAISynthesized?: boolean;
    editModeEnabled?: boolean;
    isStreaming?: boolean;
    word?: string;
}

const contentStore = useContentStore();
const notificationStore = useNotificationStore();
const props = defineProps<DefinitionItemProps>();

// Streaming indicators
const isStreaming = computed(() => props.isStreaming || false);
const isPartialDefinition = computed(() => {
    return (
        isStreaming.value &&
        (!props.definition.text || !props.definition.examples?.length)
    );
});

// Create a ref for the definition to use with edit mode
const definitionRef = computed(() => props.definition);

// Use edit mode composable
const { fields, save, regenerateComponent, canRegenerate } =
    useDefinitionEditMode(definitionRef, {
        onSave: async (updates) => {
            if (props.definition.id) {
                await contentStore.updateDefinition(
                    props.definition.id,
                    updates
                );
            } else {
                logger.error('[DefinitionItem] No definition ID available!');
            }
        },
        onRegenerate: async (component) => {
            if (props.definition.id) {
                await contentStore.regenerateDefinitionComponent(
                    props.definition.id,
                    component as 'definition' | 'examples' | 'usage_notes'
                );
            }
        },
    });

// Check if we need separator (not the first definition in the overall list)
const isSeparatorNeeded = computed(() => props.definitionIndex > 0);

// For non-AI entries, only show synonyms on the first definition to avoid repetition
const shouldShowSynonyms = computed(() => {
    if (props.isAISynthesized !== false) {
        // For AI entries or undefined, always show synonyms
        return (
            props.definition.synonyms && props.definition.synonyms.length > 0
        );
    }
    // For non-AI entries, only show on first definition
    return (
        props.isFirstInGroup &&
        props.definition.synonyms &&
        props.definition.synonyms.length > 0
    );
});

const emit = defineEmits<{
    regenerate: [index: number];
    searchWord: [word: string];
    addToWordlist: [word: string];
}>();

// Handle example updates
async function handleExampleUpdate(index: number, value: string) {
    if (props.definition.examples && props.definition.examples[index]) {
        const example = props.definition.examples[index];
        if (example.id) {
            try {
                // Update via the examples API endpoint
                await contentStore.updateExample(
                    props.definition.id,
                    example.id,
                    value
                );
                // Update local state after successful save
                example.text = value;
            } catch (error) {
                logger.error(
                    '[DefinitionItem] Failed to update example:',
                    error
                );
                notificationStore.showNotification({
                    type: 'error',
                    message: 'Failed to update example',
                    duration: 3000,
                });
            }
        } else {
            logger.warn('[DefinitionItem] Example has no ID, cannot update');
        }
    }
}

// Handle individual example regeneration
async function handleExampleRegenerate(index: number) {
    if (
        props.definition.examples &&
        props.definition.examples[index]?.type === 'generated' &&
        props.definition.id
    ) {
        // Call store method to regenerate single example
        emit('regenerate', props.definitionIndex);
    }
}
</script>
