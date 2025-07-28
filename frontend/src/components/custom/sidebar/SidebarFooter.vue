<template>
    <div class="border-border flex-shrink-0 border-t p-4">
        <div v-if="!collapsed" class="flex items-center gap-3">
            <div
                class="from-primary/20 to-primary/10 border-primary/20 flex h-8 w-8 items-center justify-center rounded-full border bg-gradient-to-br"
            >
                <User :size="14" class="text-primary" />
            </div>
            <div class="min-w-0 flex-1">
                <div class="truncate text-sm font-medium">Demo User</div>
                <div class="text-muted-foreground truncate text-xs">
                    demo@floridify.com
                </div>
            </div>
        </div>
        <div v-else class="flex justify-center">
            <div
                class="from-primary/20 to-primary/10 border-primary/20 flex h-8 w-8 items-center justify-center rounded-full border bg-gradient-to-br"
            >
                <User :size="14" class="text-primary" />
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { User } from 'lucide-vue-next';

interface Props {
    collapsed: boolean;
}

defineProps<Props>();
</script>