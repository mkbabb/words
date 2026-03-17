<template>
    <CardContent
        v-if="etymology?.text"
        class="mt-6 mb-8 space-y-3 border-t border-border/50 px-4 pt-6 sm:px-6"
    >
        <h3 class="mb-3 text-3xl font-semibold tracking-wide">Etymology</h3>
        <div
            class="rounded-md border border-border/30 bg-muted/5 px-3 py-2 transition-all duration-200 hover:border-border/50 hover:bg-muted/10"
        >
            <EditableField
                v-if="editModeEnabled"
                :model-value="etymology.text"
                field-name="etymology"
                :multiline="true"
                :edit-mode="editModeEnabled"
                :can-regenerate="false"
                @update:model-value="(val: string | number | string[]) => $emit('update:text', String(val))"
            >
                <template #display>
                    <p class="text-base leading-relaxed text-foreground">
                        {{ etymology.text }}
                    </p>
                </template>
            </EditableField>
            <p v-else class="text-base leading-relaxed text-foreground">
                {{ etymology.text }}
            </p>
            <div
                v-if="etymology.language || etymology.period"
                class="flex flex-wrap gap-2 text-sm"
            >
                <span
                    v-if="etymology.language"
                    class="text-muted-foreground/70"
                >
                    <span class="font-medium">Origin:</span>
                    {{ etymology.language }}
                </span>
                <span v-if="etymology.period" class="text-muted-foreground/70">
                    <span class="font-medium">Period:</span>
                    {{ etymology.period }}
                </span>
            </div>
        </div>
    </CardContent>
</template>

<script setup lang="ts">
import { CardContent } from '@/components/ui/card';
import type { Etymology } from '@/types/api';
import EditableField from './EditableField.vue';

interface EtymologyProps {
    etymology: Etymology | null | undefined;
    editModeEnabled?: boolean;
}

withDefaults(defineProps<EtymologyProps>(), {
    editModeEnabled: false,
});

defineEmits<{
    'update:text': [value: string];
}>();
</script>
