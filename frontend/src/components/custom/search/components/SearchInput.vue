<template>
    <textarea
        ref="textareaRef"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        aria-label="Search for a word"
        role="searchbox"
        :style="{
            minHeight: `var(--search-min-h, ${minHeight}px)`,
            maxHeight: `var(--search-max-h, ${maxHeight}px)`,
            lineHeight: 'var(--search-line-height, 1.4)',
        }"
        :class="[
            'search-input-field relative z-content block w-full bg-transparent text-lg outline-none transition-[height,color,transform] duration-300 ease-out',
            'resize-none whitespace-pre-wrap break-words overflow-hidden align-top placeholder:truncate placeholder:text-muted-foreground',
            'focus:ring-0',
            {
                'text-center': textAlign === 'center',
                'text-right': textAlign === 'right',
                'text-left': textAlign === 'left',
            },
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
import { ref, watch, nextTick, onMounted } from 'vue';

interface SearchInputProps {
    placeholder?: string;
    textAlign?: 'left' | 'center' | 'right';
    disabled?: boolean;
    aiMode?: boolean;
    minHeight?: number;
    maxHeight?: number;
}

const props = withDefaults(defineProps<SearchInputProps>(), {
    placeholder: 'Enter a word...',
    textAlign: 'left',
    disabled: false,
    aiMode: false,
    minHeight: 48,
    maxHeight: 200,
});

// Use defineModel for two-way binding (Vue 3.4+)
const modelValue = defineModel<string>({ required: true });

const emit = defineEmits<{
    focus: [];
    blur: [];
    enter: [event: KeyboardEvent];
    tab: [event: KeyboardEvent];
    space: [event: KeyboardEvent];
    'arrow-down': [event: KeyboardEvent];
    'arrow-up': [event: KeyboardEvent];
    'arrow-left': [event: KeyboardEvent];
    'arrow-right': [event: KeyboardEvent];
    escape: [event: KeyboardEvent];
    'input-click': [event: MouseEvent];
}>();

const textareaRef = ref<HTMLTextAreaElement>();

const resizeTextarea = () => {
    if (!textareaRef.value) return;

    // Force a reflow to ensure accurate measurements
    textareaRef.value.style.height = 'auto';

    // Get the scroll height (content height)
    const scrollHeight = textareaRef.value.scrollHeight;

    // Ensure minimum height is respected
    const minHeightValue = props.minHeight || 48;

    // In AI mode, allow full expansion; otherwise limit to reasonable height
    const maxHeight = props.aiMode ? props.maxHeight * 2 : props.maxHeight;
    const finalHeight = Math.max(
        minHeightValue,
        Math.min(scrollHeight, maxHeight)
    );

    // Set the textarea height directly
    textareaRef.value.style.height = `${finalHeight}px`;

    // Add scrollbar if content exceeds max height
    textareaRef.value.style.overflowY =
        scrollHeight > maxHeight ? 'auto' : 'hidden';
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
    nextTick(() => {
        resizeTextarea();
    });
};

const handleBlur = () => {
    emit('blur');
};

// Watch for all changes that should trigger resize
watch(
    [modelValue, () => props.aiMode],
    () => {
        nextTick(() => {
            resizeTextarea();
        });
    },
    { immediate: true }
);

// Also resize on mount and when component becomes visible
onMounted(() => {
    resizeTextarea();
    requestAnimationFrame(() => {
        resizeTextarea();
    });
});

// Expose methods for parent component
defineExpose({
    focus: () => textareaRef.value?.focus(),
    blur: () => textareaRef.value?.blur(),
    element: textareaRef,
    resize: resizeTextarea,
});
</script>

<style scoped>
.search-input-field {
    box-sizing: border-box;
    padding-inline: var(--search-pad-start, 1rem) var(--search-pad-end, 1rem);
    padding-block: var(--search-text-pad-y, calc((var(--search-min-h, 48px) - 1.1em) / 2));
    line-height: var(--search-line-height, 1.1);
}
</style>
