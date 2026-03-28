import { computed, watch, type Ref, type ComputedRef } from 'vue';
import { useContentStore } from '@/stores';
import { useAuthStore } from '@/stores/auth';

/**
 * Manages the active source tab selection, selectable sources,
 * and the watch that auto-selects the correct source tab.
 */
export function useSourceTabManagement(
    entry: ComputedRef<any>,
    usedProviders: Ref<string[]> | ComputedRef<string[]>,
) {
    const contentStore = useContentStore();
    const authStore = useAuthStore();

    const activeSourceTab = computed({
        get: () => contentStore.activeSourceTab,
        set: (v: string) => contentStore.setActiveSourceTab(v),
    });

    const hasAISynthesis = computed(() => !!entry.value?.model_info);

    const selectableSources = computed(() => {
        const sources: string[] = [];
        if (hasAISynthesis.value) {
            sources.push('synthesis');
        }
        sources.push(...usedProviders.value);
        return sources;
    });

    const sourceSelectionDisabled = computed(
        () => selectableSources.value.length <= 1,
    );

    const effectivelyPremium = computed(
        () => authStore.isPremium || import.meta.env.DEV,
    );

    // Keep source selection valid and auto-lock when only one source exists
    watch(
        () => [
            entry.value?.word,
            selectableSources.value.join('|'),
            effectivelyPremium.value,
        ],
        () => {
            const sources = selectableSources.value;
            if (sources.length === 0) {
                activeSourceTab.value = 'synthesis';
                return;
            }

            if (sources.length === 1) {
                activeSourceTab.value = sources[0];
                return;
            }

            if (hasAISynthesis.value && effectivelyPremium.value) {
                activeSourceTab.value = 'synthesis';
                return;
            }

            if (!sources.includes(activeSourceTab.value)) {
                activeSourceTab.value = sources[0];
            }
        },
        { immediate: true },
    );

    return {
        activeSourceTab,
        hasAISynthesis,
        selectableSources,
        sourceSelectionDisabled,
    };
}
