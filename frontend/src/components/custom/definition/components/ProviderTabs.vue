<template>
  <div v-if="providerEntries.length > 0" class="px-4 sm:px-6 pb-2">
    <Tabs :default-value="'synthesized'" class="w-full">
      <TabsList class="w-full justify-start overflow-x-auto">
        <TabsTrigger value="synthesized" class="gap-1.5">
          <Sparkles :size="14" />
          Synthesized
        </TabsTrigger>
        <TabsTrigger
          v-for="entry in providerEntries"
          :key="entry.provider"
          :value="entry.provider"
          class="gap-1.5"
        >
          <component :is="getProviderIcon(entry.provider)" :size="14" />
          {{ getProviderDisplayName(entry.provider) }}
        </TabsTrigger>
      </TabsList>

      <TabsContent value="synthesized">
        <slot />
      </TabsContent>

      <TabsContent
        v-for="entry in providerEntries"
        :key="'content-' + entry.provider"
        :value="entry.provider"
      >
        <ProviderDataTab :data="entry" />
      </TabsContent>
    </Tabs>
  </div>
  <!-- No provider data: just render the default slot -->
  <template v-else>
    <slot />
  </template>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Sparkles } from 'lucide-vue-next';
import { getProviderIcon, getProviderDisplayName } from '../utils/providers';
import ProviderDataTab from './ProviderDataTab.vue';

interface ProviderTabsProps {
  providersData: Array<Record<string, any>>;
}

const props = defineProps<ProviderTabsProps>();

const providerEntries = computed(() => {
  return (props.providersData || []).filter(
    (entry) => entry.provider && entry.provider !== 'synthesis'
  );
});
</script>
