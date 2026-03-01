<template>
  <div class="space-y-4 py-2">
    <!-- Provider metadata badge -->
    <div class="flex items-center gap-2 text-xs text-muted-foreground">
      <component :is="providerIcon" :size="14" />
      <span class="font-medium">{{ providerDisplayName }}</span>
      <span v-if="data.language" class="uppercase">{{ data.language }}</span>
    </div>

    <!-- Definitions from this provider -->
    <div v-if="data.definitions?.length" class="space-y-4">
      <div
        v-for="(def, i) in data.definitions"
        :key="i"
        class="border-l-2 border-accent pl-4 space-y-2"
      >
        <div class="flex items-center gap-2">
          <span v-if="def.part_of_speech" class="text-sm font-medium italic text-muted-foreground">
            {{ def.part_of_speech }}
          </span>
          <span v-if="def.cefr_level" class="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
            {{ def.cefr_level }}
          </span>
        </div>

        <p class="text-base leading-relaxed">{{ def.text || def.definition }}</p>

        <!-- Examples -->
        <div v-if="def.examples?.length" class="space-y-1">
          <p
            v-for="(ex, j) in def.examples"
            :key="j"
            class="text-sm text-muted-foreground italic pl-3 border-l border-border"
          >
            {{ typeof ex === 'string' ? ex : ex.text }}
          </p>
        </div>

        <!-- Synonyms -->
        <div v-if="def.synonyms?.length" class="flex flex-wrap gap-1">
          <span
            v-for="syn in def.synonyms"
            :key="syn"
            class="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground"
          >
            {{ syn }}
          </span>
        </div>
      </div>
    </div>

    <!-- Raw data fallback -->
    <div v-else-if="data.raw_data" class="rounded-lg bg-muted/30 p-4">
      <pre class="text-xs text-muted-foreground whitespace-pre-wrap break-words">{{ JSON.stringify(data.raw_data, null, 2) }}</pre>
    </div>

    <!-- Etymology from this provider -->
    <div v-if="data.etymology" class="mt-4 pt-4 border-t border-border/30">
      <h4 class="text-sm font-medium mb-2">Etymology</h4>
      <p class="text-sm text-muted-foreground leading-relaxed">
        {{ typeof data.etymology === 'string' ? data.etymology : data.etymology.text || data.etymology.origin }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { getProviderIcon, getProviderDisplayName } from '../utils/providers';

interface ProviderDataTabProps {
  data: Record<string, any>;
}

const props = defineProps<ProviderDataTabProps>();

const providerIcon = computed(() => getProviderIcon(props.data.provider || ''));
const providerDisplayName = computed(() => getProviderDisplayName(props.data.provider || 'Unknown'));
</script>
