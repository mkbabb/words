<template>
    <CardContent
        v-if="etymology"
        class="space-y-3 px-3 sm:px-6 mt-8"
    >
        <h3 class="text-lg font-semibold tracking-wide">Etymology</h3>
        <p class="text-base leading-relaxed text-muted-foreground">
            {{ etymology }}
        </p>
    </CardContent>
</template>

<script setup lang="ts">
import { CardContent } from '@/components/ui/card';

interface EtymologyProps {
    etymology: string;
}

defineProps<EtymologyProps>();
</script>