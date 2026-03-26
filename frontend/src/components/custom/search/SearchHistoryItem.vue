<template>
    <HoverCard :open-delay="150" :close-delay="50">
        <HoverCardTrigger>
            <div
                :class="
                    cn(
                        'group hover-lift-md relative w-full cursor-pointer overflow-hidden rounded-lg',
                        'border border-border bg-background shadow-sm',
                        'hover:bg-accent hover:shadow-md'
                    )
                "
                @click="$emit('lookup', entry.word)"
            >
                <div
                    class="flex items-center justify-center px-2 py-2"
                >
                    <span
                        class="text-xs font-bold tracking-wider uppercase"
                    >
                        {{
                            entry.word.substring(
                                0,
                                2
                            )
                        }}
                    </span>
                </div>
            </div>
        </HoverCardTrigger>
        <HoverCardContent
            class="max-h-96 w-80"
            side="right"
            :side-offset="8"
        >
            <div class="space-y-3">
                <!-- Word Header -->
                <div
                    class="flex items-center justify-between"
                >
                    <h3
                        class="text-base font-semibold"
                    >
                        {{ entry.word }}
                    </h3>
                    <span
                        class="text-xs text-muted-foreground"
                    >
                        {{
                            formatDate(
                                entry.timestamp
                            )
                        }}
                    </span>
                </div>

                <!-- Pronunciation -->
                <div
                    v-if="
                        entry.entry.pronunciation
                            ?.phonetic
                    "
                    class="text-sm text-muted-foreground"
                >
                    {{
                        entry.entry.pronunciation
                            .phonetic
                    }}
                </div>

                <!-- Separator -->
                <hr class="border-border/30" />

                <!-- Definitions -->
                <div
                    class="max-h-48 space-y-1 overflow-x-hidden overflow-y-auto"
                >
                    <div
                        v-for="(
                            def, defIndex
                        ) in entry.entry
                            .definitions"
                        :key="defIndex"
                        class="text-sm break-words"
                    >
                        <span
                            class="font-medium text-accent-foreground"
                            >{{
                                def.part_of_speech
                            }}</span
                        >
                        <span
                            class="ml-2 text-muted-foreground"
                            >{{ def.text }}</span
                        >
                    </div>
                </div>

                <!-- Metadata -->
                <div
                    v-if="entry.entry.lookup_count"
                    class="flex justify-between border-t border-border/30 pt-2 text-xs text-muted-foreground"
                >
                    <span
                        v-if="
                            entry.entry.lookup_count
                        "
                        >Lookups:
                        {{
                            entry.entry.lookup_count
                        }}</span
                    >
                </div>
            </div>
        </HoverCardContent>
    </HoverCard>
</template>

<script setup lang="ts">
import { formatDate, cn } from '@/utils';
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui';
import type { LookupHistory } from '@/types';

interface Props {
    entry: LookupHistory;
}

defineProps<Props>();

defineEmits<{
    lookup: [word: string];
}>();
</script>
