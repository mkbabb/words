<template>
    <textarea
        ref="textareaRef"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :style="{
            minHeight: `${minHeight}px`,
            lineHeight: '1.5',
            ...style
        }"
        :class="[
            'relative z-10 w-full rounded-xl bg-transparent text-lg transition-all duration-300 ease-out outline-none',
            'placeholder:text-muted-foreground resize-none',
            'focus:ring-1 focus:ring-gray-300 dark:focus:ring-gray-600',
            'flex items-center leading-relaxed',
            {
                'text-center': textAlign === 'center',
                'text-right': textAlign === 'right',
                'text-left': textAlign === 'left'
            }
        ]"
        rows="1"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
        @keydown.enter.prevent="$emit('enter', $event)"
        @keydown.tab.prevent="$emit('tab', $event)"
        @keydown.space="$emit('space', $event)"
        @keydown.down.prevent="$emit('arrow-down', $event)"
        @keydown.up.prevent="$emit('arrow-up', $event)"
        @keydown.left="$emit('arrow-left', $event)"
        @keydown.right="$emit('arrow-right', $event)"
        @keydown.escape="$emit('escape', $event)"
        @click="$emit('input-click', $event)"
    />
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';

interface SearchInputProps {
    placeholder?: string;
    textAlign?: 'left' | 'center' | 'right';
    disabled?: boolean;
    aiMode?: boolean;
    minHeight?: number;
    style?: Record<string, any>;
}

const props = withDefaults(defineProps<SearchInputProps>(), {
    placeholder: 'Enter a word...',
    textAlign: 'left',
    disabled: false,
    aiMode: false,
    minHeight: 48,
    style: () => ({})
});

// Use defineModel for two-way binding (Vue 3.4+)
const modelValue = defineModel<string>({ required: true });

const emit = defineEmits<{
    'focus': [];
    'blur': [];
    'enter': [event: KeyboardEvent];
    'tab': [event: KeyboardEvent];
    'space': [event: KeyboardEvent];
    'arrow-down': [event: KeyboardEvent];
    'arrow-up': [event: KeyboardEvent];
    'arrow-left': [event: KeyboardEvent];
    'arrow-right': [event: KeyboardEvent];
    'escape': [event: KeyboardEvent];
    'input-click': [event: MouseEvent];
}>();

const textareaRef = ref<HTMLTextAreaElement>();

const resizeTextarea = () => {
    if (!textareaRef.value) return;
    
    // Reset height to auto to get the natural height
    textareaRef.value.style.height = 'auto';
    
    // Get the scroll height (content height)
    const scrollHeight = textareaRef.value.scrollHeight;
    
    // Set the textarea height directly
    textareaRef.value.style.height = `${scrollHeight}px`;
};

const handleInput = (event: Event) => {
    const target = event.target as HTMLTextAreaElement;
    modelValue.value = target.value;
    nextTick(() => {
        resizeTextarea();
    });
};

const handleFocus = () => {
    emit('focus');
};

const handleBlur = () => {
    emit('blur');
};

// Watch for external value changes
watch(modelValue, () => {
    nextTick(() => {
        resizeTextarea();
    });
});

// Initial resize
nextTick(() => {
    resizeTextarea();
});

// Props are used in template
void props;

// Expose methods for parent component
defineExpose({
    focus: () => textareaRef.value?.focus(),
    blur: () => textareaRef.value?.blur(),
    element: textareaRef
});
</script>