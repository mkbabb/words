<template>
  <div class="space-y-4">
    <!-- Sort Criteria Chips -->
    <div v-if="sortCriteria.length > 0" class="space-y-3">
      <div class="flex items-center justify-between">
        <h4 class="text-sm font-medium text-muted-foreground">Sort Order</h4>
        <Button
          variant="ghost"
          size="sm"
          @click.stop="clearAllCriteria"
          class="h-7 px-2 text-xs hover:text-destructive"
        >
          <X :size="12" class="mr-1" />
          Clear All
        </Button>
      </div>
      
      <div class="space-y-2">
        <TransitionGroup
          name="sort-chip"
          tag="div"
          class="flex flex-wrap gap-2"
        >
          <div
            v-for="(criterion, index) in sortCriteria"
            :key="criterion.id"
            :class="[
              'group flex items-center gap-2 px-3 py-2 rounded-lg border transition-all duration-200',
              'bg-gradient-to-r from-primary/10 to-primary/5 border-primary/20',
              'hover:from-primary/15 hover:to-primary/10 hover:border-primary/30',
              'cursor-move select-none'
            ]"
            draggable="true"
            @dragstart="handleDragStart(index)"
            @dragover.prevent
            @drop="handleDrop(index)"
          >
            <!-- Priority indicator -->
            <div class="flex items-center justify-center w-5 h-5 rounded-full bg-primary/20 text-primary text-xs font-medium">
              {{ index + 1 }}
            </div>
            
            <!-- Criterion info -->
            <div class="flex items-center gap-2 min-w-0 flex-1">
              <component :is="getCriterionIcon(criterion.field)" :size="14" class="text-primary" />
              <span class="font-medium text-sm truncate">{{ getCriterionLabel(criterion.field) }}</span>
            </div>
            
            <!-- Direction toggle -->
            <button
              @click.stop="toggleDirection(criterion.id)"
              :class="[
                'flex items-center justify-center w-6 h-6 rounded transition-colors',
                'hover:bg-primary/20 text-primary hover:text-primary-foreground'
              ]"
              :title="`Sort ${criterion.direction === 'asc' ? 'ascending' : 'descending'}`"
            >
              <ArrowUp v-if="criterion.direction === 'asc'" :size="12" />
              <ArrowDown v-else :size="12" />
            </button>
            
            <!-- Remove button -->
            <button
              @click.stop="removeCriterion(criterion.id)"
              class="flex items-center justify-center w-6 h-6 rounded transition-colors hover:bg-destructive/20 text-muted-foreground hover:text-destructive"
              title="Remove criterion"
            >
              <X :size="12" />
            </button>
          </div>
        </TransitionGroup>
      </div>
    </div>
    
    <!-- Add Criteria -->
    <div class="space-y-3">
      <h4 class="text-sm font-medium text-muted-foreground">Add Sort Criteria</h4>
      <div class="grid grid-cols-2 gap-2">
        <button
          v-for="option in availableOptions"
          :key="option.field"
          @click.stop="addCriterion(option.field)"
          :disabled="isCriterionActive(option.field)"
          :class="[
            'flex items-center gap-2 px-3 py-2 rounded-lg border transition-all duration-200',
            'text-sm font-medium text-left',
            isCriterionActive(option.field)
              ? 'bg-muted/50 border-muted text-muted-foreground cursor-not-allowed opacity-50'
              : 'bg-background hover:bg-muted/50 border-border hover:border-primary/20 hover:text-primary'
          ]"
        >
          <component :is="option.icon" :size="14" />
          {{ option.label }}
        </button>
      </div>
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
  Type
} from 'lucide-vue-next';
import { Button } from '@/components/ui/button';

import type { AdvancedSortCriterion, SortField, SortOption } from '@/types';

const props = defineProps<{
  modelValue: AdvancedSortCriterion[];
}>();

const emit = defineEmits<{
  'update:modelValue': [criteria: AdvancedSortCriterion[]];
}>();

// Local state
const sortCriteria = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
});

const draggedIndex = ref<number | null>(null);

// Available sort options
const availableOptions: SortOption[] = [
  {
    field: 'word',
    label: 'Alphabetical',
    icon: Type,
    defaultDirection: 'asc'
  },
  {
    field: 'mastery_level',
    label: 'Mastery Level',
    icon: Trophy,
    defaultDirection: 'desc'
  },
  {
    field: 'frequency',
    label: 'Frequency',
    icon: BarChart3,
    defaultDirection: 'desc'
  },
  {
    field: 'added_at',
    label: 'Date Added',
    icon: Calendar,
    defaultDirection: 'desc'
  },
  {
    field: 'last_visited',
    label: 'Last Visited',
    icon: Eye,
    defaultDirection: 'desc'
  },
  {
    field: 'next_review',
    label: 'Next Review',
    icon: Clock,
    defaultDirection: 'asc'
  }
];

// Methods
const getCriterionIcon = (field: SortField) => {
  return availableOptions.find(opt => opt.field === field)?.icon || Trophy;
};

const getCriterionLabel = (field: SortField) => {
  return availableOptions.find(opt => opt.field === field)?.label || '';
};

const isCriterionActive = (field: SortField) => {
  return sortCriteria.value.some(criterion => criterion.field === field);
};

const addCriterion = (field: SortField) => {
  if (isCriterionActive(field)) return;
  
  const option = availableOptions.find(opt => opt.field === field);
  if (!option) return;
  
  const newCriterion: AdvancedSortCriterion = {
    id: `${field}-${Date.now()}`,
    field,
    direction: option.defaultDirection
  };
  
  sortCriteria.value = [...sortCriteria.value, newCriterion];
};

const removeCriterion = (id: string) => {
  sortCriteria.value = sortCriteria.value.filter(criterion => criterion.id !== id);
};

const toggleDirection = (id: string) => {
  sortCriteria.value = sortCriteria.value.map(criterion =>
    criterion.id === id
      ? { ...criterion, direction: criterion.direction === 'asc' ? 'desc' : 'asc' }
      : criterion
  );
};

const clearAllCriteria = () => {
  sortCriteria.value = [];
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
/* Transition animations for sort chips */
.sort-chip-move,
.sort-chip-enter-active,
.sort-chip-leave-active {
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.sort-chip-enter-from {
  opacity: 0;
  transform: scale(0.8) translateY(-10px);
}

.sort-chip-leave-to {
  opacity: 0;
  transform: scale(0.8) translateY(10px);
}

.sort-chip-leave-active {
  position: absolute;
}

/* Drag cursor */
[draggable="true"] {
  cursor: grab;
}

[draggable="true"]:active {
  cursor: grabbing;
}
</style>