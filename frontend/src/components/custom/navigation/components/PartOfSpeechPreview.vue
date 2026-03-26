<template>
    <div class="space-y-3">
        <!-- Header -->
        <div>
            <div class="flex items-center justify-between">
                <h4 class="themed-cluster-title text-sm font-medium uppercase">
                    {{ partOfSpeech.type }}
                </h4>
                <span class="rounded bg-muted px-1.5 py-0.5 text-micro font-medium text-muted-foreground">
                    {{ partOfSpeech.count }} def{{ partOfSpeech.count !== 1 ? 's' : '' }}
                </span>
            </div>
            <p v-if="clusterDescription" class="mt-0.5 text-xs text-muted-foreground">
                {{ clusterDescription }}
            </p>
        </div>

        <!-- Definition Previews -->
        <div v-if="previewDefinitions.length > 0" class="space-y-2">
            <div
                v-for="(definition, idx) in previewDefinitions"
                :key="idx"
                class="rounded-md border border-border/30 bg-muted/20 px-2.5 py-2"
            >
                <p class="text-xs leading-relaxed text-foreground/80 line-clamp-2">
                    {{ definition.text }}
                </p>
                <!-- Example -->
                <div
                    v-if="definition.examples?.[0]"
                    class="mt-1 text-micro italic text-muted-foreground line-clamp-1"
                >
                    "{{ definition.examples[0].text }}"
                </div>
                <!-- Synonyms -->
                <div
                    v-if="definition.synonyms?.length > 0"
                    class="mt-1.5 flex flex-wrap gap-1"
                >
                    <span
                        v-for="syn in definition.synonyms.slice(0, 4)"
                        :key="syn"
                        class="rounded bg-muted/50 px-1.5 py-0.5 text-micro text-muted-foreground"
                    >
                        {{ syn }}
                    </span>
                    <span
                        v-if="definition.synonyms.length > 4"
                        class="text-micro text-muted-foreground/50"
                    >
                        +{{ definition.synonyms.length - 4 }}
                    </span>
                </div>
            </div>
        </div>

        <!-- More indicator -->
        <div
            v-if="definitions.length > 2"
            class="text-micro text-muted-foreground/50"
        >
            +{{ definitions.length - 2 }} more definition{{ definitions.length - 2 !== 1 ? 's' : '' }}
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useSidebarNavigation } from '../composables/useSidebarNavigation';

interface Props {
    clusterId: string;
    partOfSpeech: { type: string; count: number };
    clusterDescription?: string;
}

const props = defineProps<Props>();
const { getDefinitionsForPartOfSpeech } = useSidebarNavigation();

const definitions = computed(() => {
    return getDefinitionsForPartOfSpeech(props.clusterId, props.partOfSpeech.type);
});

const previewDefinitions = computed(() => {
    return definitions.value.slice(0, 2);
});
</script>
