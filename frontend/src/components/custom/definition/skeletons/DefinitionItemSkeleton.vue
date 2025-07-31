<template>
  <div class="border-l-2 border-accent pl-4 space-y-3 animate-pulse">
    <!-- Part of speech and definition text -->
    <div class="space-y-2">
      <div class="flex items-center gap-2">
        <Skeleton class="h-5 w-16" />
        <Skeleton class="h-4 w-8" />
      </div>
      <Skeleton class="h-6 w-full" />
      <Skeleton class="h-4 w-4/5" />
    </div>

    <!-- Synonyms/Antonyms -->
    <div class="space-y-2">
      <Skeleton class="h-4 w-20" />
      <div class="flex flex-wrap gap-1">
        <Skeleton v-for="i in 5" :key="i" class="h-6 w-16" />
      </div>
    </div>

    <!-- Examples -->
    <div class="space-y-2">
      <Skeleton class="h-4 w-16" />
      <div class="space-y-2">
        <div v-for="i in 2" :key="i" class="bg-muted/50 rounded p-3">
          <Skeleton class="h-4 w-full mb-1" />
          <Skeleton class="h-4 w-3/4" />
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex gap-2 pt-2">
      <Skeleton class="h-8 w-20" />
      <Skeleton class="h-8 w-24" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Skeleton } from '@/components/ui';
</script>