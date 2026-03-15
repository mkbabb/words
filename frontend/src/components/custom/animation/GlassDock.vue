<script setup lang="ts">
import { ref, onUnmounted } from 'vue';

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

const expanded = ref(!props.startCollapsed);
let collapseTimer: ReturnType<typeof setTimeout> | null = null;

function clearTimer() {
    if (collapseTimer) {
        clearTimeout(collapseTimer);
        collapseTimer = null;
    }
}

function scheduleCollapse() {
    if (props.manual) return;
    clearTimer();
    collapseTimer = setTimeout(() => {
        expanded.value = false;
    }, props.collapseDelay);
}

function onEnter() {
    if (props.manual) return;
    clearTimer();
    expanded.value = true;
}

function onLeave() {
    if (props.manual) return;
    scheduleCollapse();
}

function onFocusOut(e: FocusEvent) {
    if (props.manual) return;
    const root = e.currentTarget as HTMLElement;
    if (e.relatedTarget && root.contains(e.relatedTarget as Node)) return;
    scheduleCollapse();
}

function toggle() {
    clearTimer();
    expanded.value = !expanded.value;
}

function onClickSummary() {
    if (props.manual) {
        toggle();
    } else {
        clearTimer();
        expanded.value = true;
        scheduleCollapse();
    }
}

defineExpose({ expanded, expand: () => { clearTimer(); expanded.value = true; }, collapse: () => { expanded.value = false; }, toggle });
onUnmounted(clearTimer);
</script>

<template>
    <div
        class="glass-dock"
        :class="{ expanded, collapsed: !expanded }"
        @mouseenter="onEnter"
        @mouseleave="onLeave"
        @focusin="onEnter"
        @focusout="onFocusOut"
    >
        <!-- Expanded content -->
        <Transition name="dock-fade">
            <div v-if="expanded" class="dock-layer dock-layer--full">
                <slot />
            </div>
        </Transition>
        <!-- Collapsed summary -->
        <Transition name="dock-fade">
            <div v-if="!expanded" class="dock-layer dock-layer--summary" @click="onClickSummary">
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
