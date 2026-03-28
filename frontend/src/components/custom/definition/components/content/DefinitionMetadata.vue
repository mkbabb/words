<template>
    <!-- Source Attribution Labels -->
    <div
        v-if="definition.source_definitions?.length"
        class="mt-1 flex flex-wrap gap-1"
    >
        <span
            v-for="src in definition.source_definitions"
            :key="src.entry_id"
            class="inline-flex items-center rounded-md border border-border/50 bg-muted/30 px-1.5 py-0.5 text-micro font-medium text-muted-foreground"
        >
            {{ getProviderDisplayName(src.provider) }}
            <span v-if="src.entry_version" class="ml-0.5 opacity-60"
                >v{{ src.entry_version }}</span
            >
        </span>
    </div>

    <!-- Domain & Region -->
    <div
        v-if="definition.domain || definition.region"
        class="mt-3 flex flex-wrap items-center gap-3"
    >
        <EditableField
            v-if="definition.domain"
            :model-value="fields.domain.value"
            field-name="domain"
            :edit-mode="true"
            :can-regenerate="canRegenerate('domain')"
            :is-regenerating="fields.domain.isRegenerating"
            @regenerate="$emit('regenerate-component', 'domain')"
            @update:model-value="
                (val) => {
                    fields.domain.value = String(val || '');
                    fields.domain.isDirty = true;
                    $emit('save');
                }
            "
        >
            <template #display>
                <span class="text-xs text-muted-foreground">
                    Domain: {{ definition.domain }}
                </span>
            </template>
        </EditableField>

        <EditableField
            v-if="definition.region"
            :model-value="fields.region.value"
            field-name="region"
            :edit-mode="true"
            @update:model-value="
                (val) => {
                    fields.region.value = String(val || '');
                    fields.region.isDirty = true;
                    $emit('save');
                }
            "
        >
            <template #display>
                <span class="text-xs text-muted-foreground">
                    Region: {{ definition.region }}
                </span>
            </template>
        </EditableField>
    </div>

    <!-- Usage Notes -->
    <div v-if="definition.usage_notes?.length" class="mt-3 space-y-1">
        <div class="text-xs font-medium text-muted-foreground">Usage Notes</div>
        <div
            v-for="(note, i) in definition.usage_notes"
            :key="i"
            class="rounded-lg border border-border/50 bg-muted/20 px-2 py-1 text-xs"
        >
            <span class="font-medium text-muted-foreground"
                >{{ note.type }}:</span
            >
            {{ note.text }}
        </div>
    </div>

    <!-- Grammar Patterns -->
    <div v-if="definition.grammar_patterns?.length" class="mt-3 space-y-1">
        <div class="text-xs font-medium text-muted-foreground">
            Grammar Patterns
        </div>
        <div
            v-for="(pattern, i) in definition.grammar_patterns"
            :key="i"
            class="rounded-lg border border-border/50 bg-muted/20 px-2 py-1 text-xs font-mono"
        >
            {{ pattern.pattern }}
            <span
                v-if="pattern.description"
                class="ml-1 font-sans text-muted-foreground"
            >
                &mdash; {{ pattern.description }}
            </span>
        </div>
    </div>

    <!-- Collocations -->
    <div v-if="definition.collocations?.length" class="mt-3">
        <div class="text-xs font-medium text-muted-foreground mb-1">
            Collocations
        </div>
        <div class="flex flex-wrap gap-1">
            <span
                v-for="(coll, i) in definition.collocations"
                :key="i"
                class="rounded-md border border-border/50 bg-muted/30 px-1.5 py-0.5 text-xs"
            >
                {{ coll.text }}
                <span class="text-muted-foreground/50">{{ coll.type }}</span>
            </span>
        </div>
    </div>
</template>

<script setup lang="ts">
import type { TransformedDefinition } from '@/types';
import { DictionaryProvider } from '@/types/api';
import EditableField from '../editing/EditableField.vue';

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
    return (
        PROVIDER_DISPLAY_NAMES[provider] ||
        provider
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (c) => c.toUpperCase())
    );
}

interface Props {
    definition: TransformedDefinition;
    fields: any;
    canRegenerate: (component: string) => boolean;
}

defineProps<Props>();

defineEmits<{
    'regenerate-component': [component: string];
    save: [];
}>();
</script>
