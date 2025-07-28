<template>
    <div class="space-y-4 p-2">
        <div class="rounded-lg bg-muted/30 p-4 text-center">
            <FileText class="mx-auto h-8 w-8 text-muted-foreground" />
            <h3 class="mt-2 text-sm font-medium">Word List Mode</h3>
            <p class="mt-1 text-xs text-muted-foreground">
                Upload a word list to process multiple words at once
            </p>
        </div>
        
        <!-- Placeholder sections -->
        <div class="space-y-3">
            <div class="rounded-md border border-dashed border-muted-foreground/30 p-3">
                <p class="text-xs font-medium text-muted-foreground">Word Lists</p>
                <p class="mt-1 text-xs text-muted-foreground">Your uploaded word lists will appear here</p>
            </div>
            
            <div class="rounded-md border border-dashed border-muted-foreground/30 p-3">
                <p class="text-xs font-medium text-muted-foreground">Processing Status</p>
                <p class="mt-1 text-xs text-muted-foreground">Track batch processing progress</p>
            </div>
            
            <div class="rounded-md border border-dashed border-muted-foreground/30 p-3">
                <p class="text-xs font-medium text-muted-foreground">Export Options</p>
                <p class="mt-1 text-xs text-muted-foreground">Download results in various formats</p>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { FileText } from 'lucide-vue-next';
</script>