<template>
    <div
        v-if="isMounted && isAdmin"
        class="absolute top-2 right-2 z-overlay"
    >
        <GlassDock ref="dockRef" manual :start-collapsed="!editModeEnabled">
            <!-- Collapsed summary: click expands dock AND enters edit mode -->
            <template #collapsed>
                <Tooltip>
                    <TooltipTrigger as-child>
                        <button class="dock-icon-btn" @click.stop="handleCollapsedClick">
                            <Edit2 :size="20" />
                        </button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" :side-offset="6">
                        Enter edit mode
                    </TooltipContent>
                </Tooltip>
            </template>

            <!-- Expanded toolbar — card theme far-left, edit toggle far-right -->
            <div class="flex items-center gap-1">
                <template v-if="editModeEnabled">
                    <!-- Card Theme (far left) -->
                    <Tooltip>
                        <TooltipTrigger as-child>
                            <button class="dock-icon-btn" @click="toggleDropdown">
                                <Layers :size="20" />
                            </button>
                        </TooltipTrigger>
                        <TooltipContent side="bottom" :side-offset="6">
                            Card Theme
                        </TooltipContent>
                    </Tooltip>

                    <span class="dock-separator" />

                    <!-- Add Image -->
                    <Tooltip>
                        <TooltipTrigger as-child>
                            <button class="dock-icon-btn" @click="$emit('add-image')">
                                <ImagePlus :size="20" />
                            </button>
                        </TooltipTrigger>
                        <TooltipContent side="bottom" :side-offset="6">
                            Add Image
                        </TooltipContent>
                    </Tooltip>

                    <!-- Version History -->
                    <Tooltip>
                        <TooltipTrigger as-child>
                            <button class="dock-icon-btn" @click="$emit('toggle-version-history')">
                                <History :size="20" />
                            </button>
                        </TooltipTrigger>
                        <TooltipContent side="bottom" :side-offset="6">
                            Version History
                        </TooltipContent>
                    </Tooltip>

                    <!-- Re-synthesize -->
                    <Tooltip>
                        <TooltipTrigger as-child>
                            <button class="dock-icon-btn" @click="showVersionSelector = !showVersionSelector">
                                <RefreshCw :size="20" />
                            </button>
                        </TooltipTrigger>
                        <TooltipContent side="bottom" :side-offset="6">
                            Re-synthesize
                        </TooltipContent>
                    </Tooltip>

                    <span class="dock-separator" />
                </template>

                <!-- Edit toggle (far right — checkmark when active, pencil when collapsed) -->
                <button
                    class="dock-icon-btn"
                    :class="editModeEnabled && 'active'"
                    @click="handleEditToggle"
                >
                    <Edit2 v-if="!editModeEnabled" :size="20" />
                    <Check v-else :size="20" />
                </button>
            </div>
        </GlassDock>

        <!-- Theme dropdown -->
        <Transition name="dropdown">
            <div
                v-if="showDropdown && editModeEnabled"
                class="absolute top-full right-0 z-dropdown mt-2 min-w-[140px] origin-top-right rounded-lg border border-border/30 bg-background/92 backdrop-blur-md text-popover-foreground shadow-lg p-1"
                @click.stop
            >
                <button
                    v-for="option in themes"
                    :key="option.value"
                    @click="selectTheme(option.value)"
                    :class="[
                        'flex w-full items-center rounded-md px-2 py-1.5 text-sm',
                        'transition-colors duration-150 hover:bg-accent hover:text-accent-foreground',
                        'focus-visible:bg-accent focus-visible:text-accent-foreground focus-visible:outline-none',
                        modelValue === option.value &&
                            'bg-accent text-accent-foreground font-medium',
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
        </Transition>

        <!-- Provider Version Selector Modal -->
        <Transition name="dropdown">
            <div
                v-if="showVersionSelector && word"
                class="absolute top-full right-0 z-dropdown mt-2 w-96 rounded-lg border border-border/30 bg-background/92 backdrop-blur-md p-4 shadow-lg"
                @click.stop
            >
                <ProviderVersionSelector
                    :word="word"
                    :currentVersion="currentVersion"
                    @close="showVersionSelector = false"
                    @synthesized="handleSynthesized"
                />
            </div>
        </Transition>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Edit2, Check, History, RefreshCw, Layers, ImagePlus } from 'lucide-vue-next';
import { Tooltip, TooltipTrigger, TooltipContent } from '@mkbabb/glass-ui';
import { GlassDock } from '@mkbabb/glass-ui';
import { CARD_THEMES } from '../constants';
import { useAuthStore } from '@/stores/auth';
import type { CardVariant } from '@/types';
import ProviderVersionSelector from './metadata/ProviderVersionSelector.vue';

interface ThemeSelectorProps {
    isMounted: boolean;
    showDropdown: boolean;
    editModeEnabled?: boolean;
    word?: string;
    currentVersion?: string;
}

const props = defineProps<ThemeSelectorProps>();

const modelValue = defineModel<CardVariant>({ required: true });

const auth = useAuthStore();
const isAdmin = auth.isAdmin;

const emit = defineEmits<{
    'toggle-dropdown': [];
    'toggle-edit-mode': [];
    'toggle-version-history': [];
    'resynthesize': [];
    'add-image': [];
}>();

const dockRef = ref<InstanceType<typeof GlassDock>>();
const showVersionSelector = ref(false);
const themes = CARD_THEMES;

const handleCollapsedClick = () => {
    dockRef.value?.expand();
    emit('toggle-edit-mode');
};

const handleEditToggle = () => {
    emit('toggle-edit-mode');
    // If we're exiting edit mode, collapse the dock
    if (props.editModeEnabled) {
        dockRef.value?.collapse();
    }
};

const handleSynthesized = () => {
    showVersionSelector.value = false;
    emit('resynthesize');
};

const toggleDropdown = () => {
    emit('toggle-dropdown');
};

const selectTheme = (theme: CardVariant) => {
    modelValue.value = theme;
    emit('toggle-dropdown');
};
</script>

<style scoped>
/* Dock button styles (matches Fourier dock-buttons.css) */
.dock-icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 9999px;
    border: none;
    background: transparent;
    color: var(--color-muted-foreground);
    cursor: pointer;
    transition: all 0.2s ease;
    flex-shrink: 0;
    padding: 0;
}
.dock-icon-btn:hover:not(:disabled) {
    background: color-mix(in srgb, var(--color-foreground) 8%, transparent);
    color: var(--color-foreground);
    transform: scale(1.1);
}
.dock-icon-btn:active:not(:disabled) {
    transform: scale(0.92);
}
.dock-icon-btn:focus-visible {
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--color-ring) 40%, transparent);
    outline: none;
}
.dock-icon-btn.active {
    background: color-mix(in srgb, var(--color-foreground) 8%, transparent);
    color: var(--color-foreground);
}

.dock-separator {
    width: 1px;
    height: 1.5rem;
    background: color-mix(in srgb, var(--color-foreground) 20%, transparent);
    flex-shrink: 0;
}

/* dropdown transition classes are in src/assets/transitions.css */
</style>
