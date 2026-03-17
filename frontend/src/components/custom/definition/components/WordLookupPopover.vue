<template>
    <Teleport to="body">
        <!-- Floating "Define" pill -->
        <Transition name="lookup-fade">
            <button
                v-if="isPillVisible && !isPopoverVisible"
                data-word-lookup-pill
                class="lookup-popover fixed z-50 rounded-full border-2 border-border/30 bg-background/90 px-3 py-1 text-xs font-medium text-primary shadow-cartoon-sm backdrop-blur-md transition-[background,box-shadow] duration-200 hover:bg-background/95 hover:shadow-cartoon-sm-hover"
                :style="pillStyle"
                @mousedown.prevent.stop="onPillClick"
            >
                Define
            </button>
        </Transition>

        <!-- Mini-definition popover -->
        <Transition name="lookup-fade">
            <div
                v-if="isPopoverVisible"
                data-word-lookup-popover
                class="lookup-popover fixed z-50 w-64 rounded-xl border-2 border-border/30 bg-background/90 p-3 shadow-cartoon-sm backdrop-blur-md"
                :style="{ ...popoverStyle, backgroundImage: 'var(--paper-clean-texture)', backgroundBlendMode: 'multiply' }"
            >
                <!-- Loading state -->
                <div v-if="loading" class="space-y-1.5">
                    <span class="text-base font-semibold text-foreground">
                        {{ selectedWord }}
                    </span>
                    <div class="h-1.5 w-full overflow-hidden rounded-full bg-muted/40">
                        <div
                            class="h-full w-full animate-pulse rounded-full"
                            :style="{ background: rainbowGradient }"
                        />
                    </div>
                </div>

                <!-- Content -->
                <template v-else-if="preview">
                    <!-- Word + pronunciation -->
                    <div class="flex items-baseline gap-2 pb-1.5">
                        <span class="text-base font-semibold text-foreground">
                            {{ preview.word }}
                        </span>
                        <span
                            v-if="preview.pronunciation?.ipa"
                            class="text-xs text-foreground/50"
                        >
                            /{{ preview.pronunciation.ipa }}/
                        </span>
                    </div>

                    <hr class="border-border/40" />

                    <!-- Definition -->
                    <div v-if="preview.definition" class="py-1.5">
                        <span class="text-micro font-medium text-primary/80">
                            {{ preview.definition.part_of_speech }}
                        </span>
                        <p class="mt-0.5 line-clamp-3 text-sm font-serif leading-relaxed text-foreground/80">
                            {{ preview.definition.text }}
                        </p>
                    </div>
                    <div v-else class="py-1.5 text-xs text-foreground/50 italic">
                        No definition found
                    </div>

                    <hr class="border-border/40" />

                    <!-- Actions -->
                    <div class="flex items-center gap-1 pt-1.5">
                        <button
                            class="group flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium text-foreground/70 transition-all duration-200 hover:scale-105 hover:bg-muted/30 hover:text-foreground active:scale-95"
                            @click="handleLookup"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="transition-transform duration-200 group-hover:scale-110"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                            Look up
                        </button>
                        <span class="mx-0.5 h-4 w-px bg-border/40" />
                        <button
                            class="group flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium text-foreground/70 transition-all duration-200 hover:scale-105 hover:bg-muted/30 hover:text-foreground active:scale-95"
                            @click="handleAddToWordlist"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="transition-transform duration-200 group-hover:scale-110"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
                            Wordlist
                        </button>
                    </div>
                </template>

                <!-- No cached entry — offer to do a full lookup -->
                <div v-else>
                    <div class="flex items-baseline gap-2 pb-1.5">
                        <span class="text-base font-semibold text-foreground">
                            {{ selectedWord }}
                        </span>
                    </div>
                    <hr class="border-border/40" />
                    <p class="py-1.5 text-xs text-foreground/50">
                        Not in dictionary yet
                    </p>
                    <hr class="border-border/40" />
                    <div class="flex items-center gap-1 pt-1.5">
                        <button
                            class="group flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium text-foreground/70 transition-all duration-200 hover:scale-105 hover:bg-muted/30 hover:text-foreground active:scale-95"
                            @click="handleLookup"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="transition-transform duration-200 group-hover:scale-110"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                            Look up &amp; synthesize
                        </button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import { lookupApi, type WordPreview } from '@/api/lookup';
import { generateRainbowGradient } from '@/utils/animations';

interface WordLookupPopoverProps {
    selectedWord: string;
    isPillVisible: boolean;
    isPopoverVisible: boolean;
    position: { x: number; y: number };
}

const props = defineProps<WordLookupPopoverProps>();

const emit = defineEmits<{
    showPopover: [];
    dismiss: [];
    lookup: [word: string];
    addToWordlist: [word: string];
}>();

const preview = ref<WordPreview | null>(null);
const loading = ref(false);
const rainbowGradient = generateRainbowGradient(8);

// Position with centering baked into left/top so transform is free for animation
const pillStyle = computed(() => ({
    left: `${props.position.x}px`,
    top: `${props.position.y - 8}px`,
    transform: 'translate(-50%, -100%)',
}));

const popoverStyle = computed(() => ({
    left: `${Math.max(144, Math.min(props.position.x, window.innerWidth - 144))}px`,
    top: `${props.position.y - 8}px`,
    transform: 'translate(-50%, -100%)',
}));

watch(
    () => props.isPopoverVisible,
    async (visible) => {
        if (!visible || !props.selectedWord) {
            preview.value = null;
            return;
        }
        loading.value = true;
        try {
            preview.value = await lookupApi.preview(props.selectedWord);
        } catch {
            preview.value = null;
        } finally {
            loading.value = false;
        }
    },
);

function onPillClick() {
    emit('showPopover');
}

function handleLookup() {
    emit('lookup', props.selectedWord);
    emit('dismiss');
}

function handleAddToWordlist() {
    emit('addToWordlist', props.selectedWord);
    emit('dismiss');
}
</script>

<style scoped>
/*
 * Isomorphic with HoverCardContent but safe for fixed positioning.
 * The centering transform lives in :style, so animation only touches
 * opacity + scale via a CSS custom property on the element.
 */
.lookup-popover {
    transform-origin: center bottom;
}

.lookup-fade-enter-active {
    transition: opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1),
                scale 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.lookup-fade-leave-active {
    transition: opacity 0.15s cubic-bezier(0.4, 0, 0.2, 1),
                scale 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}
.lookup-fade-enter-from {
    opacity: 0;
    scale: 0.92;
}
.lookup-fade-leave-to {
    opacity: 0;
    scale: 0.92;
}
</style>
