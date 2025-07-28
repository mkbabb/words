<template>
    <div v-if="isMounted" class="absolute top-2 right-2 z-50 flex items-center gap-2">
        <!-- Edit Mode Toggle Button -->
        <button
            @click="$emit('toggle-edit-mode')"
            class="group mt-1 rounded-lg border-2 border-border bg-background/80 p-1.5 shadow-lg backdrop-blur-sm transition-all duration-200 hover:scale-110 hover:bg-background focus:ring-0 focus:outline-none"
            :title="editModeEnabled ? 'Exit edit mode' : 'Enter edit mode'"
        >
            <Edit2 v-if="!editModeEnabled" :size="14" class="text-muted-foreground transition-colors duration-200 group-hover:text-foreground" />
            <Check v-else :size="14" class="text-muted-foreground transition-colors duration-200 group-hover:text-foreground" />
        </button>
        
        <!-- Custom dropdown with controlled animations -->
        <div class="relative">
            <button
                @click="toggleDropdown"
                class="group mt-1 rounded-lg border-2 border-border bg-background/80 p-1.5 shadow-lg backdrop-blur-sm transition-all duration-200 hover:scale-110 hover:bg-background focus:ring-0 focus:outline-none"
            >
                <ChevronLeft
                    :size="14"
                    :class="[
                        'text-muted-foreground transition-transform duration-200 group-hover:text-foreground',
                        showDropdown && 'rotate-90',
                    ]"
                />
            </button>

            <Transition
                enter-active-class="transition-all duration-400 ease-apple-spring"
                leave-active-class="transition-all duration-250 ease-apple-bounce-in"
                enter-from-class="opacity-0 scale-95 -translate-y-2"
                enter-to-class="opacity-100 scale-100 translate-y-0"
                leave-from-class="opacity-100 scale-100 translate-y-0"
                leave-to-class="opacity-0 scale-95 -translate-y-2"
            >
                <div
                    v-if="showDropdown"
                    class="absolute top-full right-0 z-60 mt-4 min-w-[140px] origin-top-right rounded-md border bg-popover text-popover-foreground shadow-md"
                    @click.stop
                >
                    <div class="p-1">
                        <div class="px-2 py-1.5 text-sm font-semibold">
                            Card Theme
                        </div>
                        <div class="my-1 h-px bg-border"></div>

                        <button
                            v-for="option in themes"
                            :key="option.value"
                            @click="selectTheme(option.value)"
                            :class="[
                                'flex w-full items-center rounded-sm px-2 py-1.5 text-sm',
                                'transition-colors hover:bg-accent hover:text-accent-foreground',
                                'focus:bg-accent focus:text-accent-foreground focus:outline-none',
                                modelValue === option.value && 'bg-accent text-accent-foreground',
                            ]"
                        >
                            <div class="flex items-center gap-2">
                                <div
                                    :class="[
                                        'h-2 w-2 rounded-full border',
                                        modelValue === option.value
                                            ? 'border-primary bg-primary'
                                            : 'border-muted-foreground',
                                    ]"
                                ></div>
                                {{ option.label }}
                            </div>
                        </button>
                    </div>
                </div>
            </Transition>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ChevronLeft, Edit2, Check } from 'lucide-vue-next';
import { CARD_THEMES } from '../constants';
import type { CardVariant } from '@/types';

interface ThemeSelectorProps {
    isMounted: boolean;
    showDropdown: boolean;
    editModeEnabled?: boolean;
}

defineProps<ThemeSelectorProps>();

// Modern Vue 3.4+ pattern - using defineModel for two-way binding
const modelValue = defineModel<CardVariant>({ required: true });

const emit = defineEmits<{
    'toggle-dropdown': [];
    'toggle-edit-mode': [];
}>();

const themes = CARD_THEMES;

const toggleDropdown = () => {
    emit('toggle-dropdown');
};

const selectTheme = (theme: CardVariant) => {
    modelValue.value = theme;
    emit('toggle-dropdown'); // Close dropdown after selection
};
</script>