import { ref } from 'vue';

/**
 * Composable for trigger-and-reset animation state.
 * Returns an `isAnimating` ref that auto-resets to false after `duration` ms.
 */
export function useAnimationToggle(duration = 600) {
    const isAnimating = ref(false);

    const trigger = () => {
        isAnimating.value = true;
        setTimeout(() => {
            isAnimating.value = false;
        }, duration);
    };

    return { isAnimating, trigger };
}
