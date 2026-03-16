<template>
    <div class="themed-card themed-shadow-lg rounded-lg bg-background/95 p-2 backdrop-blur-sm">
        <nav class="scrollbar-thin max-h-[calc(100vh-8rem)] space-y-0 overflow-y-auto">
            <WordlistControlsPanel use-store compact />
        </nav>
    </div>
</template>

<script setup lang="ts">
import WordlistControlsPanel from '@/components/custom/search/components/WordlistControlsPanel.vue';
</script>
