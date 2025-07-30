<template>
  <span class="editable-field-wrapper relative inline-block group">
    <span 
      ref="contentRef"
      @dblclick="handleDoubleClick"
      @blur="handleBlur"
      @keydown="handleKeydown"
      @input="handleInput"
      :contenteditable="isEditing"
      :class="[
        isEditing && 'focus:outline-none'
      ]"
      :data-placeholder="placeholder"
    >
      <slot name="display" :value="modelValue">
        {{ displayValue }}
      </slot>
    </span>
    
    <!-- Hover action buttons - positioned absolutely to not affect flow -->
    <span
      v-if="editMode && !isEditing"
      class="absolute -top-3 -right-3 opacity-0 group-hover:opacity-100 transition-opacity duration-150 flex gap-1 pointer-events-none z-10"
    >
      <button
        @click.stop="startEdit"
        class="pointer-events-auto rounded-full bg-background border border-border p-1 shadow-sm hover:bg-muted transition-colors"
        :title="`Edit ${fieldName}`"
      >
        <Edit2 class="h-3 w-3 text-muted-foreground" />
      </button>
      <button
        v-if="canRegenerate"
        @click.stop="$emit('regenerate')"
        :disabled="isRegenerating"
        class="pointer-events-auto rounded-full bg-background border border-border p-1 shadow-sm hover:bg-muted transition-colors disabled:opacity-50"
        :title="`Regenerate ${fieldName}`"
      >
        <RefreshCw
          :class="['h-3 w-3 text-muted-foreground', isRegenerating && 'animate-spin']"
        />
      </button>
    </span>
    
    <div v-if="errors.length > 0" class="mt-2">
      <p
        v-for="error in errors"
        :key="error"
        class="text-sm text-destructive"
      >
        {{ error }}
      </p>
    </div>
  </span>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted, type PropType } from 'vue';
import { RefreshCw, Edit2 } from 'lucide-vue-next';
import { useMagicKeys, whenever } from '@vueuse/core';

const props = defineProps({
  modelValue: {
    type: [String, Number, Array] as PropType<string | number | string[]>,
    required: true,
  },
  fieldName: {
    type: String,
    default: 'field',
  },
  multiline: {
    type: Boolean,
    default: false,
  },
  editMode: {
    type: Boolean,
    default: false,
  },
  canRegenerate: {
    type: Boolean,
    default: false,
  },
  isRegenerating: {
    type: Boolean,
    default: false,
  },
  errors: {
    type: Array as PropType<string[]>,
    default: () => [],
  },
  validator: {
    type: Function as PropType<(value: any) => string | undefined>,
  },
  placeholder: {
    type: String,
    default: '',
  },
});

const emit = defineEmits<{
  'update:modelValue': [value: string | number | string[]];
  'edit:start': [];
  'edit:end': [];
  'regenerate': [];
}>();

const isEditing = ref(false);
const contentRef = ref<HTMLElement>();
const originalValue = ref('');

const displayValue = computed(() => {
  if (Array.isArray(props.modelValue)) {
    return props.modelValue.join(', ');
  }
  return String(props.modelValue || '');
});


function startEdit() {
  if (isEditing.value) return;
  
  isEditing.value = true;
  originalValue.value = displayValue.value;
  emit('edit:start');
  
  nextTick(() => {
    if (contentRef.value) {
      // Focus and select all text
      contentRef.value.focus();
      const range = document.createRange();
      range.selectNodeContents(contentRef.value);
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(range);
    }
  });
}

function handleDoubleClick() {
  if (props.editMode && !isEditing.value) {
    startEdit();
  }
}

function getTextContent(): string {
  if (!contentRef.value) return '';
  // Get text content, preserving line breaks for multiline fields
  return contentRef.value.textContent || '';
}

function handleInput() {
  // Track changes but don't update model until save
  // This allows for escape to cancel
}

function save() {
  const currentValue = getTextContent();
  console.log('[EditableField] Saving:', props.fieldName, 'currentValue:', currentValue, 'originalValue:', originalValue.value);
  
  if (props.validator) {
    const error = props.validator(currentValue);
    if (error) {
      console.log('[EditableField] Validation failed:', error);
      return;
    }
  }
  
  let newValue: string | number | string[];
  
  if (Array.isArray(props.modelValue)) {
    newValue = currentValue
      .split(',')
      .map(s => s.trim())
      .filter(s => s);
  } else if (typeof props.modelValue === 'number') {
    newValue = Number(currentValue);
  } else {
    newValue = currentValue;
  }
  
  // Only emit if value actually changed
  if (JSON.stringify(newValue) !== JSON.stringify(props.modelValue)) {
    console.log('[EditableField] Emitting update:', newValue);
    emit('update:modelValue', newValue);
  } else {
    console.log('[EditableField] No changes detected');
  }
  
  isEditing.value = false;
  emit('edit:end');
}

function cancel() {
  isEditing.value = false;
  emit('edit:end');
}

// Keyboard handling
const target = computed(() => contentRef.value || document.body);
const keys = useMagicKeys({ target });

// Save with Shift+Enter (for multiline) or Enter (for single line)
function handleKeydown(event: KeyboardEvent) {
  if (!isEditing.value) return;
  
  if (event.key === 'Escape') {
    event.preventDefault();
    cancel();
  } else if (event.key === 'Enter' && (!props.multiline || event.shiftKey)) {
    event.preventDefault();
    save();
  }
}

// Save with Cmd/Ctrl+S
whenever(keys.cmd_s, () => {
  if (isEditing.value) save();
});
whenever(keys.ctrl_s, () => {
  if (isEditing.value) save();
});

function handleBlur() {
  if (!isEditing.value) return;
  
  // Small delay to allow click events on buttons to fire
  setTimeout(() => {
    if (isEditing.value) {
      const currentValue = getTextContent();
      if (currentValue !== originalValue.value) {
        save();
      } else {
        cancel();
      }
    }
  }, 200);
}

// Watch for external edit mode changes
watch(() => props.editMode, (newVal) => {
  if (!newVal && isEditing.value) {
    cancel();
  }
});

// Watch for model value changes to update displayed content
watch(() => props.modelValue, () => {
  // Force component re-render when value changes to preserve slot styling
  if (!isEditing.value) {
    nextTick();
  }
});

// Listen for global save event
const handleSaveAll = () => {
  if (isEditing.value) {
    save();
  }
};

onMounted(() => {
  document.addEventListener('save-all-edits', handleSaveAll);
});

onUnmounted(() => {
  document.removeEventListener('save-all-edits', handleSaveAll);
});
</script>

<style scoped>
@media (prefers-reduced-motion: reduce) {
  .animate-wiggle-bounce {
    animation: none;
    border: 2px dashed rgb(var(--color-primary) / 0.3);
  }
}

/* Contenteditable styling to maintain visual consistency */
[contenteditable="true"] {
  cursor: text;
  -webkit-user-select: text;
  user-select: text;
  /* Prevent any layout changes */
  display: inline;
  outline: none;
}

/* Remove all outlines to maintain exact visual flow */
[contenteditable="true"]:focus {
  outline: none;
  background-color: rgb(var(--color-primary) / 0.05);
  border-radius: 2px;
}

/* Placeholder styling for empty contenteditable */
[contenteditable="true"]:empty:before {
  content: attr(data-placeholder);
  color: rgb(var(--color-muted-foreground) / 0.5);
}
</style>