<template>
    <CardContent
        v-if="etymology?.text"
        class="space-y-3 px-4 sm:px-6 mt-6 mb-8 border-t border-border/50 pt-6"
    >
        <h3 class="text-3xl font-semibold tracking-wide mb-3">Etymology</h3>
        <div class="px-3 py-2 rounded-md border border-border/30 bg-muted/5 hover:border-border/50 hover:bg-muted/10 transition-all duration-200">
            <p class="text-base leading-relaxed text-foreground">
                {{ etymology.text }}
            </p>
            <div v-if="etymology.language || etymology.period" class="flex flex-wrap gap-2 text-sm">
                <span v-if="etymology.language" class="text-muted-foreground/80">
                    <span class="font-medium">Origin:</span> {{ etymology.language }}
                </span>
                <span v-if="etymology.period" class="text-muted-foreground/80">
                    <span class="font-medium">Period:</span> {{ etymology.period }}
                </span>
            </div>
        </div>
    </CardContent>
</template>

<script setup lang="ts">
import { CardContent } from '@/components/ui/card';
import type { Etymology } from '@/types/api';

interface EtymologyProps {
    etymology: Etymology | null | undefined;
}

defineProps<EtymologyProps>();
</script>