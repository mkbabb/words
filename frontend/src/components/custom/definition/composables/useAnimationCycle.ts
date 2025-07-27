import { onMounted, onUnmounted } from 'vue';

export function useAnimationCycle(callback: () => void, interval: number = 5000) {
    let intervalId: number | null = null;

    const startCycle = () => {
        if (intervalId) return;
        intervalId = window.setInterval(callback, interval);
    };

    const stopCycle = () => {
        if (intervalId) {
            clearInterval(intervalId);
            intervalId = null;
        }
    };

    onMounted(() => {
        startCycle();
    });

    onUnmounted(() => {
        stopCycle();
    });

    return {
        startCycle,
        stopCycle
    };
}