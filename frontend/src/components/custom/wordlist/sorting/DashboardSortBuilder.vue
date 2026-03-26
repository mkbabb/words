<template>
    <div>
        <!-- Compact mode: vertical list with icons (progressive sidebar) -->
        <div v-if="compact" class="space-y-1">
            <div
                v-for="option in sortOptions"
                :key="option.value"
                :class="[
                    'flex items-center gap-1.5 rounded-md px-2 py-1.5 transition-fast select-none cursor-pointer',
                    modelValue === option.value
                        ? 'border border-primary/20 bg-gradient-to-r from-primary/10 to-primary/5 hover:from-primary/15 hover:to-primary/10 hover:border-primary/30 hover:shadow-sm'
                        : 'border border-transparent hover:border-border/50 hover:bg-muted/60 hover:shadow-sm',
                ]"
                @click="$emit('update:modelValue', option.value)"
            >
                <component
                    :is="option.icon"
                    :size="14"
                    :class="modelValue === option.value ? 'text-primary' : 'text-muted-foreground'"
                />
                <span
                    :class="[
                        'truncate text-sm font-medium',
                        modelValue === option.value ? 'text-foreground' : 'text-muted-foreground',
                    ]"
                >
                    {{ option.label }}
                </span>
            </div>
        </div>

        <!-- Non-compact mode: grid layout (search controls dropdown) -->
        <div v-else class="grid grid-cols-2 gap-1.5">
            <button
                v-for="option in sortOptions"
                :key="option.value"
                @click="$emit('update:modelValue', option.value)"
                :class="[
                    'flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-fast select-none',
                    modelValue === option.value
                        ? 'border border-primary/30 bg-primary/10 text-primary shadow-sm hover:bg-primary/15'
                        : 'border border-border/50 bg-background hover:border-primary/20 hover:bg-muted/50 hover:shadow-sm text-muted-foreground hover:text-foreground',
                ]"
            >
                <component :is="option.icon" :size="14" class="shrink-0" />
                <span class="truncate">{{ option.label }}</span>
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { Clock, Type, BarChart3, Trophy } from 'lucide-vue-next';
import { markRaw, type Component } from 'vue';

withDefaults(defineProps<{
    modelValue: string;
    compact?: boolean;
}>(), {
    compact: false,
});

defineEmits<{
    'update:modelValue': [value: string];
}>();

const sortOptions: Array<{ value: string; label: string; icon: Component }> = [
    { value: 'last_accessed', label: 'Recent', icon: markRaw(Clock) },
    { value: 'name', label: 'Alphabetical', icon: markRaw(Type) },
    { value: 'word_count', label: 'Word Count', icon: markRaw(BarChart3) },
    { value: 'mastery', label: 'Mastery', icon: markRaw(Trophy) },
];
</script>
