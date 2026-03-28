import { ref, computed, watch, onUnmounted, type Ref } from 'vue';
import { wordlistApi, lookupApi } from '@/api';
import type { DueWordItem, ReviewResult, SM2Quality } from '@/types/wordlist';
import type { SynthesizedDictionaryEntry } from '@/types';
import {
    getCardStateLabelFull,
    getCardStateBadgeClasses,
} from '../../utils/formatting';

export interface UseReviewSessionOptions {
    wordlistId: Ref<string>;
    selectedWords: Ref<string[] | undefined>;
    modelValue: Ref<boolean>;
    onClose: () => void;
    onSessionClose: () => void;
}

/**
 * Review session state machine.
 *
 * Manages the lifecycle of a review session: loading due words,
 * tracking the current card, handling reveal + quality submission,
 * keyboard shortcuts, and session completion.
 */
export function useReviewSession(options: UseReviewSessionOptions) {
    const { wordlistId, selectedWords, modelValue, onClose, onSessionClose } = options;

    // Session state
    const dueWords = ref<DueWordItem[]>([]);
    const currentIndex = ref(0);
    const results = ref<{ word: string; quality: SM2Quality; result: ReviewResult }[]>([]);
    const sessionComplete = ref(false);

    // UI state
    const isLoading = ref(false);
    const isRevealed = ref(false);
    const isFlipped = ref(false);
    const isLookingUp = ref(false);
    const isSubmitting = ref(false);
    const lookupError = ref<string | null>(null);
    const lookupTimedOut = ref(false);
    const revealedDefinition = ref<SynthesizedDictionaryEntry | null>(null);

    // Mastery transitions tracking
    const masteryTransitions = ref<Array<{ word: string; from: string; to: string }>>([]);

    // Computeds
    const currentWord = computed<DueWordItem>(() => dueWords.value[currentIndex.value]);

    const progressRatio = computed(() => {
        if (dueWords.value.length === 0) return 0;
        return currentIndex.value / dueWords.value.length;
    });

    const currentStateLabel = computed(() =>
        getCardStateLabelFull(currentWord.value?.card_state),
    );

    const currentStateBadgeClasses = computed(() =>
        getCardStateBadgeClasses(currentWord.value?.card_state),
    );

    // -----------------------------------------------------------------------
    // Core actions
    // -----------------------------------------------------------------------

    async function fetchSession() {
        isLoading.value = true;
        try {
            const response = await wordlistApi.getReviewSession(wordlistId.value);
            const data = response.data ?? response;
            dueWords.value = data.words ?? [];

            if (selectedWords.value?.length) {
                const selected = new Set(selectedWords.value);
                dueWords.value = dueWords.value.filter((w) => selected.has(w.word));
            }

            currentIndex.value = 0;
            results.value = [];
            sessionComplete.value = false;
            isRevealed.value = false;
        } catch {
            dueWords.value = [];
        } finally {
            isLoading.value = false;
        }
    }

    function resetState() {
        dueWords.value = [];
        currentIndex.value = 0;
        results.value = [];
        sessionComplete.value = false;
        isRevealed.value = false;
        isFlipped.value = false;
        isLookingUp.value = false;
        isSubmitting.value = false;
        lookupError.value = null;
        lookupTimedOut.value = false;
        revealedDefinition.value = null;
        masteryTransitions.value = [];
    }

    async function handleReveal() {
        isLookingUp.value = true;
        lookupError.value = null;
        lookupTimedOut.value = false;
        revealedDefinition.value = null;

        try {
            const entry = await lookupApi.lookup(currentWord.value.word, { timeout: 15000 });
            revealedDefinition.value = entry;
        } catch (err: any) {
            if (err?.code === 'ECONNABORTED' || err?.message?.toLowerCase().includes('timeout')) {
                lookupTimedOut.value = true;
            } else {
                lookupError.value = err?.message ?? 'Failed to look up definition';
            }
        } finally {
            isLookingUp.value = false;
            isRevealed.value = true;
            isFlipped.value = true;
        }
    }

    async function handleQualitySubmit(quality: SM2Quality) {
        isSubmitting.value = true;
        try {
            const response = await wordlistApi.submitWordReview(wordlistId.value, {
                word: currentWord.value.word,
                quality,
            });
            const result: ReviewResult = response.data ?? response;

            results.value.push({ word: currentWord.value.word, quality, result });

            if (result.mastery_changed && result.previous_mastery) {
                masteryTransitions.value.push({
                    word: currentWord.value.word,
                    from: result.previous_mastery,
                    to: result.mastery_level,
                });
            }

            if (currentIndex.value + 1 < dueWords.value.length) {
                currentIndex.value++;
                isRevealed.value = false;
                isFlipped.value = false;
                isLookingUp.value = false;
                lookupError.value = null;
                lookupTimedOut.value = false;
                revealedDefinition.value = null;
            } else {
                sessionComplete.value = true;
            }
        } catch {
            // Allow retrying
        } finally {
            isSubmitting.value = false;
        }
    }

    // -----------------------------------------------------------------------
    // Keyboard handler
    // -----------------------------------------------------------------------

    function handleKeyboard(event: KeyboardEvent) {
        if (sessionComplete.value || isLoading.value || dueWords.value.length === 0) return;

        if (event.key === ' ' && !isRevealed.value && !isLookingUp.value) {
            event.preventDefault();
            handleReveal();
            return;
        }

        if (!isRevealed.value || isSubmitting.value) return;

        const keyMap: Record<string, SM2Quality> = { '1': 0, '2': 2, '3': 4, '4': 5 };
        const quality = keyMap[event.key];
        if (quality !== undefined) {
            event.preventDefault();
            handleQualitySubmit(quality);
        }
    }

    function handleEscape(event: KeyboardEvent) {
        if (event.key === 'Escape') onClose();
    }

    // -----------------------------------------------------------------------
    // Lifecycle watches
    // -----------------------------------------------------------------------

    watch(
        modelValue,
        (open) => {
            const lockVal = open ? 'hidden' : '';
            document.body.style.overflow = lockVal;
            document.documentElement.style.overflow = lockVal;
            if (open) {
                document.addEventListener('keydown', handleEscape);
                document.addEventListener('keydown', handleKeyboard);
            } else {
                document.removeEventListener('keydown', handleEscape);
                document.removeEventListener('keydown', handleKeyboard);
            }
        },
    );

    watch(
        modelValue,
        async (isOpen) => {
            if (isOpen) {
                await fetchSession();
            } else {
                resetState();
            }
        },
    );

    onUnmounted(() => {
        document.body.style.overflow = '';
        document.documentElement.style.overflow = '';
        document.removeEventListener('keydown', handleEscape);
        document.removeEventListener('keydown', handleKeyboard);
    });

    return {
        // Session state
        dueWords,
        currentIndex,
        results,
        sessionComplete,

        // UI state
        isLoading,
        isRevealed,
        isFlipped,
        isLookingUp,
        isSubmitting,
        lookupError,
        lookupTimedOut,
        revealedDefinition,
        masteryTransitions,

        // Computeds
        currentWord,
        progressRatio,
        currentStateLabel,
        currentStateBadgeClasses,

        // Actions
        fetchSession,
        resetState,
        handleReveal,
        handleQualitySubmit,

        // Close handlers (passed through for template use)
        handleClose: onClose,
        handleSessionClose: onSessionClose,
    };
}
