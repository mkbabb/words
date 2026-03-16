<template>
    <div>
        <!-- Compact mode: vertical list (progressive sidebar) -->
        <div v-if="compact" class="space-y-1">
            <TransitionGroup
                name="sort-item"
                tag="div"
                class="space-y-1"
            >
                <div
                    v-for="option in sortedOptions"
                    :key="option.field"
                    :class="[
                        'flex items-center transition-all duration-200 select-none',
                        'gap-1.5 rounded-md px-2 py-1.5',
                        isActive(option.field)
                            ? 'border border-primary/20 bg-gradient-to-r from-primary/10 to-primary/5 hover:from-primary/15 hover:to-primary/10 hover:border-primary/30 hover:shadow-sm'
                            : 'border border-transparent hover:border-border/50 hover:bg-muted/60 hover:shadow-sm cursor-pointer',
                        isActive(option.field) && 'cursor-grab active:cursor-grabbing',
                    ]"
                    :draggable="isActive(option.field)"
                    @dragstart="isActive(option.field) && handleDragStart(getActiveIndex(option.field))"
                    @dragover.prevent
                    @drop="isActive(option.field) && handleDrop(getActiveIndex(option.field))"
                    @click="!isActive(option.field) && addCriterion(option.field)"
                >
                    <div
                        v-if="isActive(option.field)"
                        class="flex shrink-0 items-center justify-center rounded-full bg-primary/20 font-bold text-primary tabular-nums h-5 w-5 text-xs"
                    >
                        {{ getActiveIndex(option.field) + 1 }}
                    </div>
                    <div class="flex min-w-0 flex-1 items-center gap-1.5">
                        <component
                            :is="option.icon"
                            :size="14"
                            :class="isActive(option.field) ? 'text-primary' : 'text-muted-foreground'"
                        />
                        <span
                            :class="[
                                'truncate text-sm font-medium',
                                isActive(option.field) ? 'text-foreground' : 'text-muted-foreground',
                            ]"
                        >
                            {{ option.label }}
                        </span>
                    </div>
                    <template v-if="isActive(option.field)">
                        <button
                            @click.stop="toggleDirection(getCriterionId(option.field))"
                            class="flex shrink-0 items-center justify-center rounded transition-colors text-primary hover:bg-primary/20 h-5 w-5"
                        >
                            <ArrowUp v-if="getDirection(option.field) === 'asc'" :size="14" />
                            <ArrowDown v-else :size="14" />
                        </button>
                        <button
                            @click.stop="removeCriterion(getCriterionId(option.field))"
                            class="flex shrink-0 items-center justify-center rounded text-muted-foreground/50 transition-colors hover:bg-destructive/20 hover:text-destructive h-5 w-5"
                        >
                            <X :size="10" />
                        </button>
                    </template>
                </div>
            </TransitionGroup>
        </div>

        <!-- Non-compact mode: grid layout (search controls dropdown) -->
        <div v-else class="grid grid-cols-3 gap-1.5">
            <button
                v-for="option in availableOptions"
                :key="option.field"
                @click="toggleCriterion(option.field)"
                :class="[
                    'relative flex items-center gap-1.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-all duration-200 select-none',
                    isActive(option.field)
                        ? 'border border-primary/30 bg-primary/10 text-primary shadow-sm hover:bg-primary/15'
                        : 'border border-border/50 bg-background hover:border-primary/20 hover:bg-muted/50 hover:shadow-sm text-muted-foreground hover:text-foreground',
                ]"
            >
                <!-- Priority badge (top-left overlay) -->
                <div
                    v-if="isActive(option.field)"
                    class="absolute -top-1.5 -left-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[9px] font-bold text-primary-foreground shadow-sm"
                >
                    {{ getActiveIndex(option.field) + 1 }}
                </div>

                <component :is="option.icon" :size="14" class="shrink-0" />
                <span class="truncate">{{ option.label }}</span>

                <!-- Direction arrow (inline, only when active) -->
                <button
                    v-if="isActive(option.field)"
                    @click.stop="toggleDirection(getCriterionId(option.field))"
                    class="ml-auto flex shrink-0 items-center justify-center rounded-full h-5 w-5 hover:bg-primary/20 transition-colors"
                >
                    <ArrowUp v-if="getDirection(option.field) === 'asc'" :size="12" />
                    <ArrowDown v-else :size="12" />
                </button>
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import {
    X,
    ArrowUp,
    ArrowDown,
    Trophy,
    BarChart3,
    Calendar,
    Eye,
    Clock,
    Type,
} from 'lucide-vue-next';

import type { AdvancedSortCriterion, SortField, SortOption } from '@/types';

const props = withDefaults(defineProps<{
    modelValue: AdvancedSortCriterion[];
    compact?: boolean;
}>(), {
    compact: false,
});

const emit = defineEmits<{
    'update:modelValue': [criteria: AdvancedSortCriterion[]];
}>();

// Local state
const sortCriteria = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value),
});

const draggedIndex = ref<number | null>(null);

// Available sort options
const availableOptions: SortOption[] = [
    {
        field: 'word',
        label: 'Alphabetical',
        icon: Type,
        defaultDirection: 'asc',
    },
    {
        field: 'mastery_level',
        label: 'Mastery Level',
        icon: Trophy,
        defaultDirection: 'desc',
    },
    {
        field: 'frequency',
        label: 'Frequency',
        icon: BarChart3,
        defaultDirection: 'desc',
    },
    {
        field: 'added_at',
        label: 'Date Added',
        icon: Calendar,
        defaultDirection: 'desc',
    },
    {
        field: 'last_visited',
        label: 'Last Visited',
        icon: Eye,
        defaultDirection: 'desc',
    },
    {
        field: 'next_review',
        label: 'Next Review',
        icon: Clock,
        defaultDirection: 'asc',
    },
];

// Active items come first, in their sort order; inactive follow in their default order
const sortedOptions = computed(() => {
    const active = sortCriteria.value
        .map(c => availableOptions.find(o => o.field === c.field))
        .filter(Boolean) as SortOption[];
    const inactive = availableOptions.filter(o => !isCriterionActive(o.field));
    return [...active, ...inactive];
});

const isActive = (field: SortField) => isCriterionActive(field);

const getActiveIndex = (field: SortField) => {
    return sortCriteria.value.findIndex(c => c.field === field);
};

const getCriterionId = (field: SortField) => {
    return sortCriteria.value.find(c => c.field === field)?.id ?? '';
};

const getDirection = (field: SortField) => {
    return sortCriteria.value.find(c => c.field === field)?.direction ?? 'asc';
};

// Methods
const isCriterionActive = (field: SortField) => {
    return sortCriteria.value.some((criterion) => criterion.field === field);
};

const addCriterion = (field: SortField) => {
    if (isCriterionActive(field)) return;

    const option = availableOptions.find((opt) => opt.field === field);
    if (!option) return;

    const newCriterion: AdvancedSortCriterion = {
        id: `${field}-${Date.now()}`,
        field,
        direction: option.defaultDirection,
    };

    sortCriteria.value = [...sortCriteria.value, newCriterion];
};

const removeCriterion = (id: string) => {
    sortCriteria.value = sortCriteria.value.filter(
        (criterion) => criterion.id !== id
    );
};

const toggleCriterion = (field: SortField) => {
    if (isCriterionActive(field)) {
        const id = getCriterionId(field);
        removeCriterion(id);
    } else {
        addCriterion(field);
    }
};

const toggleDirection = (id: string) => {
    sortCriteria.value = sortCriteria.value.map((criterion) =>
        criterion.id === id
            ? {
                  ...criterion,
                  direction: criterion.direction === 'asc' ? 'desc' : 'asc',
              }
            : criterion
    );
};

// Drag and drop handlers
const handleDragStart = (index: number) => {
    draggedIndex.value = index;
};

const handleDrop = (dropIndex: number) => {
    if (draggedIndex.value === null || draggedIndex.value === dropIndex) {
        draggedIndex.value = null;
        return;
    }

    const newCriteria = [...sortCriteria.value];
    const draggedItem = newCriteria.splice(draggedIndex.value, 1)[0];
    newCriteria.splice(dropIndex, 0, draggedItem);

    sortCriteria.value = newCriteria;
    draggedIndex.value = null;
};
</script>

<style scoped>
.sort-item-move,
.sort-item-enter-active,
.sort-item-leave-active {
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.sort-item-enter-from {
    opacity: 0;
    transform: translateX(-10px);
}
.sort-item-leave-to {
    opacity: 0;
    transform: translateX(10px);
}
</style>
