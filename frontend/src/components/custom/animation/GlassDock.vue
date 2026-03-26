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
    persistent: props.manual,
});

// Handle startCollapsed / manual props — force expand immediately
onMounted(() => {
    if (!props.startCollapsed || props.manual) {
        expand(true);
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
    background: var(--color-card-82);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--color-border-50);
    box-shadow: 0 4px 16px var(--color-foreground-8);
    overflow: visible;
    white-space: nowrap;
    transition:
        transform 0.25s var(--ease-apple-spring),
        opacity 0.18s var(--ease-apple-smooth);
    transform: translateZ(0);
    will-change: transform, opacity;
}

.glass-dock.collapsed {
    width: auto;
    min-width: 2.5rem;
    cursor: pointer;
    padding: 0.375rem 0.625rem;
    background: var(--color-card-92);
    border-color: var(--color-border-70);
    box-shadow:
        0 2px 8px var(--color-foreground-12),
        0 0 0 1px var(--color-foreground-6);
}

.glass-dock.collapsed:hover {
    background: var(--color-card-96);
    border-color: var(--color-border);
    box-shadow:
        0 4px 20px var(--color-foreground-18),
        0 0 0 1px var(--color-foreground-10);
    transform: translateZ(0) scale(1.015);
}

.dock-layer {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    min-height: 2.5rem;
    transform: translateZ(0);
}

.dock-layer--full {
    overflow: visible;
    transition: opacity 0.28s var(--ease-apple-smooth), transform 0.28s var(--ease-apple-spring);
}

.dock-layer--summary {
    gap: 0.375rem;
    transition: opacity 0.24s var(--ease-apple-smooth), transform 0.24s var(--ease-apple-spring);
}

/* dock-fade transition classes are in src/assets/transitions.css */
</style>
