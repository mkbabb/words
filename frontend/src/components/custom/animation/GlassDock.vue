<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useDockState } from '@/composables/useDockState';

const props = withDefaults(
    defineProps<{
        collapseDelay?: number;
        startCollapsed?: boolean;
        /** When true, only collapses via explicit toggle — no auto-collapse on mouse leave */
        manual?: boolean;
    }>(),
    {
        collapseDelay: 2000,
        startCollapsed: true,
        manual: false,
    },
);

const rootEl = ref<HTMLElement | null>(null);

const {
    expanded,
    isPinned,
    onMouseEnter,
    onMouseLeave,
    onFocusIn,
    onFocusOut,
    onClickCollapsed,
    keepOpen,
    release,
    expand,
    collapse,
} = useDockState({
    collapseDelay: props.manual ? Number.MAX_SAFE_INTEGER : props.collapseDelay,
    rootEl,
});

// Handle startCollapsed / manual props
onMounted(() => {
    if (!props.startCollapsed || props.manual) {
        // Force expand immediately, bypassing the ignoreEvents guard
        expand();
        // If the ignoreEvents guard blocked it, retry after the guard lifts
        setTimeout(() => {
            if (!expanded.value) {
                expand();
            }
        }, 650);
    }
});

function toggle() {
    if (expanded.value) {
        collapse();
    } else {
        expand();
    }
}

// In manual mode, wrap mouse/focus handlers to no-op
function handleMouseEnter() {
    if (props.manual) return;
    onMouseEnter();
}

function handleMouseLeave(e: MouseEvent) {
    if (props.manual) return;
    onMouseLeave(e);
}

function handleFocusIn() {
    if (props.manual) return;
    onFocusIn();
}

function handleFocusOut(e: FocusEvent) {
    if (props.manual) return;
    onFocusOut(e);
}

function handleClickCollapsed() {
    if (props.manual) {
        toggle();
    } else {
        onClickCollapsed();
    }
}

defineExpose({ expanded, isPinned, expand, collapse, keepOpen, release, toggle });
</script>

<template>
    <div
        ref="rootEl"
        class="glass-dock"
        :class="{ expanded, collapsed: !expanded }"
        @mouseenter="handleMouseEnter"
        @mouseleave="handleMouseLeave"
        @focusin="handleFocusIn"
        @focusout="handleFocusOut"
    >
        <!-- Expanded content -->
        <Transition name="dock-fade">
            <div v-if="expanded" class="dock-layer dock-layer--full" :inert="!expanded">
                <slot />
            </div>
        </Transition>
        <!-- Collapsed summary -->
        <Transition name="dock-fade">
            <div
                v-if="!expanded"
                class="dock-layer dock-layer--summary"
                :inert="expanded"
                @click="handleClickCollapsed"
            >
                <slot name="collapsed" />
            </div>
        </Transition>
    </div>
</template>

<style scoped>
.glass-dock {
    display: inline-flex;
    align-items: center;
    padding: 0.375rem 0.75rem;
    border-radius: 9999px;
    background: color-mix(in srgb, var(--color-card) 82%, transparent);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid color-mix(in srgb, var(--color-border) 50%, transparent);
    box-shadow: 0 4px 16px color-mix(in srgb, var(--color-foreground) 8%, transparent);
    overflow: visible;
    white-space: nowrap;
    transition:
        padding 0.2s var(--ease-apple-smooth),
        box-shadow 0.2s var(--ease-apple-smooth),
        transform 0.2s var(--ease-apple-smooth),
        opacity 0.15s var(--ease-apple-default);
    will-change: transform;
}

.glass-dock.collapsed {
    width: auto;
    min-width: 2.5rem;
    cursor: pointer;
    padding: 0.375rem 0.625rem;
    background: color-mix(in srgb, var(--color-card) 92%, transparent);
    border-color: color-mix(in srgb, var(--color-border) 70%, transparent);
    box-shadow:
        0 2px 8px color-mix(in srgb, var(--color-foreground) 12%, transparent),
        0 0 0 1px color-mix(in srgb, var(--color-foreground) 6%, transparent);
}

.glass-dock.collapsed:hover {
    background: color-mix(in srgb, var(--color-card) 96%, transparent);
    border-color: var(--color-border);
    box-shadow:
        0 4px 20px color-mix(in srgb, var(--color-foreground) 18%, transparent),
        0 0 0 1px color-mix(in srgb, var(--color-foreground) 10%, transparent);
    transform: scale(1.02);
}

.dock-layer {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    min-height: 2.5rem;
}

.dock-layer--full {
    overflow: visible;
    transition: opacity 0.2s ease;
}

.dock-layer--summary {
    gap: 0.375rem;
    transition: opacity 0.15s ease;
}

.dock-fade-enter-active {
    transition: opacity 0.2s ease 0.08s;
}
.dock-fade-leave-active {
    transition: opacity 0.12s ease;
    position: absolute;
}
.dock-fade-enter-from,
.dock-fade-leave-to {
    opacity: 0;
}
</style>
