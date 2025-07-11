<template>
  <TabsList
    v-bind="props"
    :class="cn('inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground gap-1', props.class)"
  >
    <slot />
  </TabsList>
</template>

<script setup lang="ts">
import { type HTMLAttributes, computed } from 'vue'
import { TabsList, type TabsListProps } from 'radix-vue'
import { cn } from '@/utils'

const props = defineProps<TabsListProps & { class?: HTMLAttributes['class'] }>()
</script>