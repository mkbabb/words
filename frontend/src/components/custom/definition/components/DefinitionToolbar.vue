<template>
    <!-- Admin Edit Dock — anchor point below separator, zero height, no flow impact -->
    <div class="relative h-0 z-50">
        <ThemeSelector
            v-model="modelValue"
            :isMounted="isMounted"
            :showDropdown="showDropdown"
            :editModeEnabled="editModeEnabled"
            :word="word"
            :currentVersion="currentVersion"
            @toggle-dropdown="$emit('toggle-dropdown')"
            @toggle-edit-mode="$emit('toggle-edit-mode')"
            @toggle-version-history="$emit('toggle-version-history')"
            @resynthesize="$emit('resynthesize')"
            @add-image="$emit('add-image')"
        />
    </div>
</template>

<script setup lang="ts">
import { ThemeSelector } from './index';
import type { CardVariant } from '@/types';

const modelValue = defineModel<CardVariant>({ required: true });

defineProps<{
    isMounted: boolean;
    showDropdown: boolean;
    editModeEnabled: boolean;
    word?: string;
    currentVersion?: string;
}>();

defineEmits<{
    'toggle-dropdown': [];
    'toggle-edit-mode': [];
    'toggle-version-history': [];
    'resynthesize': [];
    'add-image': [];
}>();
</script>
