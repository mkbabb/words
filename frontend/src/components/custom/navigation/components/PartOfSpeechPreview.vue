<template>
    <div class="space-y-3">
        <div class="flex items-center justify-between">
            <h4 class="themed-cluster-title text-sm font-semibold uppercase">
                {{ partOfSpeech.type }}
            </h4>
            <span class="text-xs opacity-70">{{ partOfSpeech.count }} definitions</span>
        </div>
        <div class="space-y-2">
            <div
                v-for="(definition, idx) in previewDefinitions"
                :key="idx"
                class="space-y-1"
            >
                <p class="themed-definition-text text-sm leading-relaxed">
                    {{ definition.definition || definition.text }}
                </p>
                <div
                    v-if="definition.examples?.generated?.[0] || definition.examples?.literature?.[0]"
                    class="themed-example-text text-xs italic opacity-75"
                >
                    "{{ (definition.examples.generated[0] || definition.examples.literature[0])?.sentence }}"
                </div>
            </div>
            <div
                v-if="definitions.length > 2"
                class="text-xs opacity-60"
            >
                +{{ definitions.length - 2 }} more definitions
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useSidebarNavigation } from '../composables/useSidebarNavigation';

interface Props {
    clusterId: string;
    partOfSpeech: { type: string; count: number };
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