<template>
  <div class="space-y-4 animate-pulse">
    <!-- Definition Cluster Header -->
    <div class="flex items-center gap-2 mb-4">
      <Skeleton class="h-6 w-20" />
      <Skeleton class="h-4 w-4 rounded-full" />
    </div>

    <!-- Definition Items -->
    <div class="space-y-6">
      <div v-for="i in definitionCount" :key="i" class="border-l-2 border-accent pl-4 space-y-3">
        <!-- Part of speech and definition text -->
        <div class="space-y-2">
          <div class="flex items-center gap-2">
            <Skeleton class="h-5 w-16" />
            <Skeleton class="h-4 w-8" />
          </div>
          <Skeleton class="h-6 w-full" />
          <Skeleton class="h-4 w-3/4" />
        </div>

        <!-- Synonyms -->
        <div class="space-y-2">
          <Skeleton class="h-4 w-20" />
          <div class="flex flex-wrap gap-1">
            <Skeleton v-for="j in 4" :key="j" class="h-6 w-16" />
          </div>
        </div>

        <!-- Examples placeholder -->
        <div class="space-y-2">
          <Skeleton class="h-4 w-16" />
          <div class="space-y-1">
            <Skeleton v-for="k in 2" :key="k" class="h-4 w-full" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Skeleton } from '@/components/ui';

interface Props {
  definitionCount?: number;
}

withDefaults(defineProps<Props>(), {
  definitionCount: 2
});
</script>