<template>
    <Teleport to="body">
        <Transition
            :css="false"
            @before-enter="beforeEnter"
            @enter="overlayEnter"
            @leave="overlayLeave"
        >
            <div
                v-if="isOpen"
                class="fixed inset-0 z-max flex flex-col"
                @click="handleBackdropClick"
            >
                <!-- Backdrop -->
                <div
                    ref="backdropRef"
                    class="absolute inset-0 bg-background/60 dark:bg-background/70 backdrop-blur-2xl"
                />

                <!-- Close button -->
                <button
                    class="absolute top-4 right-4 z-controls flex h-8 w-8 items-center justify-center rounded-full glass-subtle text-foreground/70 transition-colors hover:bg-background/90 hover:text-foreground"
                    @click.stop="emit('close')"
                >
                    <X :size="16" />
                </button>

                <!-- Title -->
                <div class="relative z-content pt-6 text-center">
                    <p class="text-micro font-medium tracking-widest text-muted-foreground/50 uppercase">
                        Version History
                    </p>
                    <h2
                        v-if="word"
                        class="mt-1 text-2xl font-semibold text-foreground/60 tracking-tight"
                    >
                        {{ word }}
                    </h2>
                </div>

                <!-- Main content area -->
                <div
                    ref="contentRef"
                    class="relative z-content flex flex-1 items-center justify-center gap-4 overflow-hidden px-4"
                    @click.stop
                >
                    <Transition name="view-switch" mode="out-in">
                        <!-- Expanded: full entry view -->
                        <div
                            v-if="expandedView && selectedVersion && (hydratedEntry || versionDetail)"
                            key="expanded"
                            class="flex h-full w-full items-start justify-center py-4"
                        >
                            <TimeMachineExpandedView
                                :version="selectedVersion"
                                :hydrated-entry="hydratedEntry"
                                :is-current-version="
                                    selectedVersion?.version === currentVersion
                                "
                                :rolling-back="rollingBack"
                                :diff-fields="diffFields"
                                :text-changes="textChanges"
                                @collapse="$emit('toggleExpanded')"
                                @rollback="$emit('rollback')"
                            />
                        </div>

                        <!-- Compact: card with navigation arrows -->
                        <div
                            v-else
                            key="compact"
                            class="flex w-full items-center justify-center gap-4"
                        >
                            <!-- Left arrow (older) -->
                            <button
                                class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full glass-subtle text-muted-foreground transition-[color,background-color,opacity] hover:bg-background/70 hover:text-foreground disabled:pointer-events-none disabled:opacity-30"
                                :disabled="isOldest"
                                @click="$emit('navigatePrev')"
                            >
                                <ChevronLeft :size="20" />
                            </button>

                            <!-- Version card -->
                            <TimeMachineVersionCard
                                :version="selectedVersion"
                                :detail="versionDetail"
                                :detail-loading="detailLoading"
                                :rolling-back="rollingBack"
                                :is-current-version="
                                    selectedVersion?.version === currentVersion
                                "
                                :direction="navigationDirection"
                                :diff-fields="diffFields"
                                @rollback="$emit('rollback')"
                                @expand="$emit('toggleExpanded')"
                            />

                            <!-- Right arrow (newer) -->
                            <button
                                class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full glass-subtle text-muted-foreground transition-[color,background-color,opacity] hover:bg-background/70 hover:text-foreground disabled:pointer-events-none disabled:opacity-30"
                                :disabled="isNewest"
                                @click="$emit('navigateNext')"
                            >
                                <ChevronRight :size="20" />
                            </button>
                        </div>
                    </Transition>
                </div>

                <!-- Timeline scrubber (bottom) — hidden when expanded -->
                <Transition name="timeline-fade">
                    <div
                        v-if="!expandedView"
                        ref="timelineRef"
                        class="relative z-content"
                        @click.stop
                    >
                        <!-- Loading state -->
                        <div v-if="loading" class="flex justify-center py-6">
                            <div
                                class="h-2 w-32 animate-pulse rounded-full bg-muted"
                            />
                        </div>

                        <!-- Empty state -->
                        <div
                            v-else-if="versions.length === 0"
                            class="py-6 text-center text-xs text-muted-foreground/50"
                        >
                            No version history available.
                        </div>

                        <!-- Timeline -->
                        <TimeMachineTimeline
                            v-else
                            :versions="versions"
                            :selected-index="selectedIndex"
                            @select="$emit('selectVersion', $event)"
                        />
                    </div>
                </Transition>
            </div>
        </Transition>
    </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue';
import { X, ChevronLeft, ChevronRight } from 'lucide-vue-next';
import TimeMachineVersionCard from '../TimeMachineVersionCard.vue';
import TimeMachineTimeline from '../TimeMachineTimeline.vue';
import TimeMachineExpandedView from '../TimeMachineExpandedView.vue';
import type { VersionSummary, VersionDetailResponse } from '@/types/api';
import type { SynthesizedDictionaryEntry } from '@/types';
import type { VersionDiff, TextChange } from '../../composables/useTimeMachine';

interface Props {
    isOpen: boolean;
    word?: string;
    currentVersion?: string;
    versions: VersionSummary[];
    selectedIndex: number;
    selectedVersion: VersionSummary | null;
    versionDetail: VersionDetailResponse | null;
    versionDiff: VersionDiff | null;
    diffFields: Set<string>;
    textChanges: Map<string, TextChange[]>;
    hydratedEntry: SynthesizedDictionaryEntry | null;
    navigationDirection: 'forward' | 'backward';
    loading: boolean;
    detailLoading: boolean;
    rollingBack: boolean;
    isNewest: boolean;
    isOldest: boolean;
    expandedView: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    close: [];
    selectVersion: [index: number];
    navigateNext: [];
    navigatePrev: [];
    rollback: [];
    toggleExpanded: [];
}>();

function handleBackdropClick(event: Event) {
    const target = event.target as Element;
    // Only close if clicking the outer container or the backdrop itself
    if (target === event.currentTarget || target === backdropRef.value) {
        if (props.expandedView) {
            emit('toggleExpanded');
        } else {
            emit('close');
        }
    }
}

// Animation refs
const backdropRef = ref<HTMLDivElement>();
const contentRef = ref<HTMLDivElement>();
const timelineRef = ref<HTMLDivElement>();

// Prevent body scroll when open
watch(
    () => props.isOpen,
    (open) => {
        document.body.style.overflow = open ? 'hidden' : '';
    }
);

onUnmounted(() => {
    document.body.style.overflow = '';
});

// JS-driven transitions for overlay enter/leave
function beforeEnter() {
    if (backdropRef.value) {
        backdropRef.value.style.transition = 'none';
        backdropRef.value.style.opacity = '0';
    }
    if (contentRef.value) {
        contentRef.value.style.transition = 'none';
        contentRef.value.style.opacity = '0';
        contentRef.value.style.transform = 'scale(0.92) translateY(20px)';
    }
    if (timelineRef.value) {
        timelineRef.value.style.transition = 'none';
        timelineRef.value.style.opacity = '0';
        timelineRef.value.style.transform = 'translateY(20px)';
    }
}

function overlayEnter(_el: Element, done: () => void) {
    if (!backdropRef.value || !contentRef.value) {
        done();
        return;
    }

    void backdropRef.value.offsetHeight;

    requestAnimationFrame(() => {
        if (!backdropRef.value || !contentRef.value) {
            done();
            return;
        }

        // Backdrop fade — fast
        backdropRef.value.style.transition = 'opacity 200ms cubic-bezier(0.4, 0, 0.2, 1)';
        backdropRef.value.style.opacity = '1';

        // Content slide up — no bounce, slightly staggered
        setTimeout(() => {
            if (!contentRef.value) { done(); return; }
            contentRef.value.style.transition = 'opacity 250ms cubic-bezier(0.4, 0, 0.2, 1), transform 250ms cubic-bezier(0.4, 0, 0.2, 1)';
            contentRef.value.style.opacity = '1';
            contentRef.value.style.transform = 'scale(1) translateY(0)';

            if (timelineRef.value) {
                timelineRef.value.style.transition = 'opacity 200ms cubic-bezier(0.4, 0, 0.2, 1) 80ms, transform 200ms cubic-bezier(0.4, 0, 0.2, 1) 80ms';
                timelineRef.value.style.opacity = '1';
                timelineRef.value.style.transform = 'translateY(0)';
            }

            setTimeout(done, 300);
        }, 30);
    });
}

function overlayLeave(el: Element, done: () => void) {
    const backdrop = el.querySelector('[class*="backdrop-blur"]') as HTMLElement;
    const content = contentRef.value || (el.children[2] as HTMLElement);
    const timeline = timelineRef.value || (el.children[3] as HTMLElement);

    if (!backdrop) { done(); return; }

    requestAnimationFrame(() => {
        if (content) {
            content.style.transition = 'opacity 150ms cubic-bezier(0.4, 0, 0.2, 1), transform 150ms cubic-bezier(0.4, 0, 0.2, 1)';
            content.style.opacity = '0';
            content.style.transform = 'scale(0.97) translateY(8px)';
        }
        if (timeline) {
            timeline.style.transition = 'opacity 120ms cubic-bezier(0.4, 0, 0.2, 1)';
            timeline.style.opacity = '0';
        }
        backdrop.style.transition = 'opacity 180ms cubic-bezier(0.4, 0, 0.2, 1)';
        backdrop.style.opacity = '0';

        setTimeout(done, 200);
    });
}
</script>

<style scoped>
/* View switch: compact <-> expanded */
.view-switch-enter-active {
    transition: opacity 200ms var(--ease-apple-smooth), transform 200ms var(--ease-apple-smooth);
}
.view-switch-leave-active {
    transition: opacity 120ms var(--ease-apple-default), transform 120ms var(--ease-apple-default);
}
.view-switch-enter-from {
    opacity: 0;
    transform: scale(0.96);
}
.view-switch-leave-to {
    opacity: 0;
    transform: scale(0.98);
}

/* Timeline fade for hide/show */
.timeline-fade-enter-active {
    transition: opacity 200ms var(--ease-apple-smooth), transform 200ms var(--ease-apple-smooth);
}
.timeline-fade-leave-active {
    transition: opacity 120ms var(--ease-apple-default);
}
.timeline-fade-enter-from {
    opacity: 0;
    transform: translateY(6px);
}
.timeline-fade-leave-to {
    opacity: 0;
}
</style>
