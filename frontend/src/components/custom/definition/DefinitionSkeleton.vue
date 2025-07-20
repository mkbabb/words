<template>
  <div class="space-y-8">
    <!-- Word Header Skeleton -->
    <Card>
      <CardHeader>
        <div class="flex items-center justify-between">
          <Skeleton class="h-8 w-48" />
          <Skeleton class="h-8 w-24" />
        </div>

        <!-- Pronunciation Skeleton -->
        <div class="flex items-center gap-4 pt-2">
          <div class="flex items-center gap-2">
            <Skeleton class="h-6 w-32" />
            <Skeleton class="h-5 w-16" />
          </div>
          <Skeleton class="h-8 w-28" />
        </div>
      </CardHeader>
    </Card>

    <!-- Definition Cards Skeleton -->
    <div class="space-y-6">
      <Card v-for="i in 2" :key="i" class="animate-pulse">
        <CardHeader>
          <div class="flex items-center gap-2">
            <Skeleton class="h-6 w-16 animate-pulse" />
            <Skeleton class="h-4 w-4 animate-pulse" />
          </div>
        </CardHeader>

        <CardContent class="space-y-4">
          <div class="space-y-3">
            <div class="border-accent border-l-2 pl-4">
              <Skeleton class="mb-2 h-6 w-full animate-pulse" />
              <Skeleton class="mb-2 h-4 w-3/4 animate-pulse" />

              <!-- Synonyms Skeleton -->
              <div class="mt-2 flex flex-wrap gap-1">
                <Skeleton class="h-5 w-16 animate-pulse" />
                <Skeleton
                  v-for="j in 3"
                  :key="j"
                  class="h-5 w-20 animate-pulse"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Etymology Skeleton -->
    <Card>
      <CardHeader>
        <Skeleton class="h-6 w-24" />
      </CardHeader>
      <CardContent>
        <Skeleton class="h-4 w-full" />
        <Skeleton class="mt-2 h-4 w-2/3" />
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { Card, CardHeader, CardContent, Skeleton } from '@/components/ui';
</script>
