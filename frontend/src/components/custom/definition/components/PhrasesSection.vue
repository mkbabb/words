<template>
    <CardContent
        v-if="phrases?.length"
        class="mt-4 mb-4 space-y-3 border-t border-border/50 px-4 pt-6 sm:px-6"
    >
        <h3 class="mb-3 text-xl font-semibold tracking-wide">
            Phrases & Idioms
        </h3>
        <div class="space-y-2">
            <div
                v-for="(phrase, i) in phrases"
                :key="i"
                class="rounded-lg border border-border/20 bg-card px-3 py-2 shadow-sm transition-fast hover:border-border/40 hover:bg-card/90"
            >
                <div class="flex items-baseline gap-2">
                    <span class="font-medium text-foreground">
                        {{ phrase.phrase }}
                    </span>
                    <Badge
                        v-if="phrase.usage_register"
                        variant="outline"
                        class="text-micro h-4 px-1"
                    >
                        {{ phrase.usage_register }}
                    </Badge>
                </div>
                <p class="mt-0.5 text-sm text-muted-foreground">
                    {{ phrase.meaning }}
                </p>
                <p
                    v-if="phrase.example"
                    class="mt-1 text-xs italic text-foreground/60"
                >
                    "{{ phrase.example }}"
                </p>
            </div>
        </div>
    </CardContent>
</template>

<script setup lang="ts">
import { CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Phrase } from '@/types/api';

defineProps<{
    phrases: Phrase[] | null | undefined;
}>();
</script>
