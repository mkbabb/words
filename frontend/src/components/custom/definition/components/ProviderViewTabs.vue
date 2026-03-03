<template>
  <Tabs
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event as string)"
    class="w-full"
  >
    <!-- No TabsList — source switching is controlled by ProviderIcons in WordHeader -->

    <!-- AI Synthesis content (default slot) -->
    <TabsContent value="synthesis" class="mt-0">
      <slot />
    </TabsContent>

    <!-- Provider data tabs (pre-created for each available provider) -->
    <TabsContent
      v-for="providerName in availableProviders"
      :key="providerName"
      :value="providerName"
      class="mt-0"
    >
      <div class="px-4 pb-4 sm:px-6">
        <ProviderDataView
          v-if="getLoadedProvider(providerName)"
          :provider="getLoadedProvider(providerName)!"
        />
        <!-- Loading skeleton while provider data is being fetched -->
        <div v-else class="animate-pulse space-y-3 py-4">
          <div class="h-4 w-24 rounded bg-muted" />
          <div class="h-4 w-full rounded bg-muted" />
          <div class="h-4 w-3/4 rounded bg-muted" />
          <div class="h-4 w-1/2 rounded bg-muted" />
        </div>
      </div>
    </TabsContent>
  </Tabs>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { Tabs, TabsContent } from '@/components/ui/tabs';
import ProviderDataView from './ProviderDataView.vue';
import { providersApi, type ProviderEntry } from '@/api/providers';

interface Props {
  modelValue: string;
  word: string;
  availableProviders?: string[];
}

const props = withDefaults(defineProps<Props>(), {
  availableProviders: () => [],
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const providers = ref<ProviderEntry[]>([]);
const loaded = ref(false);

function getLoadedProvider(name: string): ProviderEntry | undefined {
  return providers.value.find((p) => p.provider === name);
}

async function loadProviders() {
  if (!props.word || loaded.value) return;
  try {
    const data = await providersApi.getWordProviders(props.word);
    providers.value = data.filter((p) => p.provider !== 'synthesis');
    loaded.value = true;
  } catch {
    // Provider data is optional — silent failure
  }
}

// Load when a non-synthesis tab is selected
watch(() => props.modelValue, (tab) => {
  if (tab !== 'synthesis' && !loaded.value) {
    loadProviders();
  }
});

// Reset when word changes
watch(() => props.word, () => {
  loaded.value = false;
  providers.value = [];
  emit('update:modelValue', 'synthesis');
});

// Pre-load on mount
onMounted(loadProviders);
</script>
