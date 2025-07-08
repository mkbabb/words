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
            <div class="pl-4 border-l-2 border-accent">
              <Skeleton class="h-6 w-full mb-2 animate-pulse" />
              <Skeleton class="h-4 w-3/4 mb-2 animate-pulse" />
              
              <!-- Synonyms Skeleton -->
              <div class="flex flex-wrap gap-1 mt-2">
                <Skeleton class="h-5 w-16 animate-pulse" />
                <Skeleton v-for="j in 3" :key="j" class="h-5 w-20 animate-pulse" />
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
        <Skeleton class="h-4 w-2/3 mt-2" />
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import Skeleton from '@/components/ui/Skeleton.vue';
</script>