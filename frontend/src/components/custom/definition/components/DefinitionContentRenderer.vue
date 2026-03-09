<template>
    <div class="space-y-0">
        <!-- Word Header -->
        <DiffSection field="languages" :diff-fields="diffFields">
            <WordHeader
                v-if="entry.word && entry.languages?.length"
                :word="entry.word"
                :languages="entry.languages"
                :pronunciation="entry.pronunciation"
                :pronunciationMode="'phonetic'"
                :providers="usedProviders"
                :isAISynthesized="!!entry.model_info"
                :activeSource="'synthesis'"
                :sourceSelectionDisabled="true"
                :sourceEntries="entry.source_entries"
            />
        </DiffSection>

        <!-- Gradient Separator -->
        <hr
            class="h-px border-0 bg-gradient-to-r from-transparent via-muted-foreground/20 to-transparent dark:via-muted-foreground/30"
        />

        <!-- Definition Clusters -->
        <DiffSection field="definitions" :diff-fields="diffFields">
            <CardContent class="space-y-4 px-4 sm:px-6">
                <DefinitionCluster
                    v-for="(cluster, clusterIndex) in groupedDefinitions"
                    :key="cluster.clusterId"
                    :cluster="cluster"
                    :clusterIndex="clusterIndex"
                    :totalClusters="groupedDefinitions.length"
                    :cardVariant="'default'"
                    :editModeEnabled="false"
                    :isStreaming="false"
                >
                    <DefinitionItem
                        v-for="(definition, defIndex) in cluster.definitions"
                        :key="`${cluster.clusterId}-${defIndex}`"
                        :definition="definition"
                        :definitionIndex="getGlobalDefinitionIndex(clusterIndex, defIndex)"
                        :isRegenerating="false"
                        :isFirstInGroup="defIndex === 0"
                        :isAISynthesized="!!entry.model_info"
                        :editModeEnabled="false"
                        :isStreaming="false"
                        :word="entry.word"
                    />
                </DefinitionCluster>
                <p
                    v-if="groupedDefinitions.length === 0"
                    class="py-6 text-center text-sm text-muted-foreground/60"
                >
                    No definitions in this version
                </p>
            </CardContent>

            <!-- Inline text diffs for definitions -->
            <div
                v-if="definitionTextChanges.length > 0"
                class="mx-4 mb-4 space-y-2 sm:mx-6"
            >
                <TextDiffBlock
                    v-for="(change, i) in definitionTextChanges"
                    :key="i"
                    :label="formatDiffPath(change.path)"
                    :old-text="change.oldValue"
                    :new-text="change.newValue"
                />
            </div>
        </DiffSection>

        <!-- Etymology -->
        <DiffSection field="etymology" :diff-fields="diffFields">
            <Etymology :etymology="normalizedEtymology" />

            <!-- Inline text diffs for etymology -->
            <div
                v-if="etymologyTextChanges.length > 0"
                class="mx-4 mb-4 space-y-2 sm:mx-6"
            >
                <TextDiffBlock
                    v-for="(change, i) in etymologyTextChanges"
                    :key="i"
                    :label="formatDiffPath(change.path)"
                    :old-text="change.oldValue"
                    :new-text="change.newValue"
                />
            </div>
        </DiffSection>

        <!-- Catch-all: text diffs for other fields not rendered above -->
        <template v-for="[field, changes] in otherTextChanges" :key="field">
            <DiffSection :field="field" :diff-fields="diffFields">
                <div class="mx-4 my-2 space-y-2 sm:mx-6">
                    <TextDiffBlock
                        v-for="(change, i) in changes"
                        :key="i"
                        :label="formatDiffPath(change.path)"
                        :old-text="change.oldValue"
                        :new-text="change.newValue"
                    />
                </div>
            </DiffSection>
        </template>

        <!-- Version metadata footer -->
        <div
            v-if="entry.id"
            class="flex justify-center pb-2"
        >
            <div
                class="flex items-center gap-2 rounded-md border border-border/30 bg-background/50 px-3 py-1 text-xs text-muted-foreground/50"
            >
                {{ entry.id }}
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, h, type FunctionalComponent } from 'vue';
import { CardContent } from '@/components/ui/card';
import {
    WordHeader,
    DefinitionCluster,
    DefinitionItem,
    Etymology,
} from './index';
import TextDiffBlock from './TextDiffBlock.vue';
import { useDefinitionGroups, useProviders } from '../composables';
import { normalizeEtymology } from '@/utils/guards';
import type { SynthesizedDictionaryEntry } from '@/types';
import type { TextChange } from '../composables/useTimeMachine';

interface Props {
    entry: SynthesizedDictionaryEntry;
    diffFields?: Set<string>;
    textChanges?: Map<string, TextChange[]>;
}

const props = withDefaults(defineProps<Props>(), {
    diffFields: () => new Set<string>(),
    textChanges: () => new Map<string, TextChange[]>(),
});

// Use the same composables as DefinitionDisplay
const entryRef = computed((): SynthesizedDictionaryEntry | null => props.entry ?? null);
const { groupedDefinitions } = useDefinitionGroups(entryRef);
const { usedProviders } = useProviders(entryRef);

const normalizedEtymology = computed(() =>
    normalizeEtymology(props.entry?.etymology)
);

const getGlobalDefinitionIndex = (clusterIndex: number, defIndex: number): number => {
    let globalIndex = 0;
    for (let i = 0; i < clusterIndex; i++) {
        globalIndex += groupedDefinitions.value[i].definitions.length;
    }
    return globalIndex + defIndex;
};

// Text changes split by field for rendering in the right section
const definitionTextChanges = computed(() => props.textChanges.get('definitions') ?? []);
const etymologyTextChanges = computed(() => props.textChanges.get('etymology') ?? []);
const otherTextChanges = computed(() => {
    const skip = new Set(['definitions', 'etymology', 'languages']);
    const entries: [string, TextChange[]][] = [];
    for (const [field, changes] of props.textChanges) {
        if (!skip.has(field)) entries.push([field, changes]);
    }
    return entries;
});

/** Format a DeepDiff path into a human-readable label */
function formatDiffPath(path: string): string {
    // root['definitions'][2]['text'] → definitions[2].text
    return path
        .replace(/^root/, '')
        .replace(/\['(\w+)'\]/g, '.$1')
        .replace(/\[(\d+)\]/g, '[$1]')
        .replace(/^\./, '');
}

// Diff section wrapper: highlights changed sections with colored left border
const DiffSection: FunctionalComponent<
    { field: string; diffFields: Set<string> },
    {},
    { default: () => any }
> = (fProps, { slots }) => {
    const changed = fProps.diffFields.has(fProps.field);
    if (!changed) {
        return h('div', {}, slots.default?.());
    }
    return h(
        'div',
        {
            class: 'relative border-l-2 border-amber-400/70 bg-amber-500/[0.04] rounded-r-lg',
        },
        [
            slots.default?.(),
            h(
                'div',
                {
                    class: 'absolute top-2 right-2 flex items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-medium text-amber-600 dark:text-amber-400',
                },
                [
                    h('span', { class: 'inline-block h-1.5 w-1.5 rounded-full bg-amber-500' }),
                    ` ${fProps.field} changed`,
                ]
            ),
        ]
    );
};
DiffSection.props = ['field', 'diffFields'];
</script>
