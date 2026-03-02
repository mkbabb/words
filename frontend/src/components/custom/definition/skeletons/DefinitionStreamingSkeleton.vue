<template>
    <div v-if="show" class="space-y-6">
        <div
            v-for="i in count"
            :key="`skeleton-${i}`"
            class="animate-pulse space-y-3 border-l-2 border-accent pl-4"
        >
            <div class="flex items-center gap-2">
                <div class="h-5 w-16 rounded bg-muted" />
                <div class="h-4 w-8 rounded bg-muted" />
            </div>
            <div class="space-y-2">
                <div class="h-6 w-full rounded bg-muted" />
                <div class="h-4 w-4/5 rounded bg-muted" />
            </div>
            <div class="flex flex-wrap gap-1">
                <div
                    v-for="j in 4"
                    :key="j"
                    class="h-6 w-16 rounded bg-muted"
                />
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
defineProps<{
    show: boolean;
    count: number;
}>();
</script>
