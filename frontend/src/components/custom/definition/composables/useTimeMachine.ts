import { ref, computed, watch, type Ref } from 'vue';
import { useDebounceFn, useMagicKeys, whenever } from '@vueuse/core';
import { versionsApi } from '@/api';
import { useAuthStore } from '@/stores/auth';
import type { VersionSummary, VersionDetailResponse } from '@/types/api';
import type { SynthesizedDictionaryEntry } from '@/types';

export interface VersionDiff {
    values_changed?: Record<string, { old_value: any; new_value: any }>;
    dictionary_item_added?: Record<string, any>;
    dictionary_item_removed?: Record<string, any>;
    iterable_item_added?: Record<string, any>;
    iterable_item_removed?: Record<string, any>;
    type_changes?: Record<
        string,
        { old_type: string; new_type: string; old_value: any; new_value: any }
    >;
}

/** Parse a DeepDiff path like "root['etymology']['text']" into a top-level field name */
function topLevelField(path: string): string {
    const match = path.match(/^root\['([^']+)'\]/);
    return match ? match[1] : path;
}

/** Extract the set of top-level fields that changed from a diff */
export function changedFields(diff: VersionDiff | null): Set<string> {
    if (!diff) return new Set();
    const fields = new Set<string>();
    for (const section of [
        diff.values_changed,
        diff.dictionary_item_added,
        diff.dictionary_item_removed,
        diff.iterable_item_added,
        diff.iterable_item_removed,
        diff.type_changes,
    ]) {
        if (!section) continue;
        for (const path of Object.keys(section)) {
            fields.add(topLevelField(path));
        }
    }
    return fields;
}

/** A single text change extracted from a diff: the path, old text, and new text. */
export interface TextChange {
    path: string;
    oldValue: string;
    newValue: string;
}

/**
 * Extract all string-valued changes from a diff, grouped by top-level field.
 * Only includes changes where both old and new values are strings (i.e., text diffs).
 */
export function extractTextChanges(
    diff: VersionDiff | null,
): Map<string, TextChange[]> {
    const result = new Map<string, TextChange[]>();
    if (!diff) return result;

    const sections = [
        diff.values_changed,
        diff.type_changes,
    ];

    for (const section of sections) {
        if (!section) continue;
        for (const [path, change] of Object.entries(section)) {
            const oldVal = change.old_value;
            const newVal = change.new_value;
            // Only include string-to-string changes (actual text diffs)
            if (typeof oldVal === 'string' && typeof newVal === 'string') {
                const field = topLevelField(path);
                if (!result.has(field)) result.set(field, []);
                result.get(field)!.push({
                    path,
                    oldValue: oldVal,
                    newValue: newVal,
                });
            }
        }
    }

    // Also capture added/removed items that are strings
    for (const [section, label] of [
        [diff.dictionary_item_added, 'added'] as const,
        [diff.dictionary_item_removed, 'removed'] as const,
    ]) {
        if (!section) continue;
        for (const [path, value] of Object.entries(section)) {
            if (typeof value === 'string') {
                const field = topLevelField(path);
                if (!result.has(field)) result.set(field, []);
                result.get(field)!.push({
                    path,
                    oldValue: label === 'removed' ? value : '',
                    newValue: label === 'added' ? value : '',
                });
            }
        }
    }

    return result;
}

export function useTimeMachine(wordRef: Ref<string | undefined>) {
    const auth = useAuthStore();

    // State
    const isOpen = ref(false);
    const versions = ref<VersionSummary[]>([]);
    const selectedIndex = ref(0);
    const versionDetail = ref<VersionDetailResponse | null>(null);
    const versionDiff = ref<VersionDiff | null>(null);
    const navigationDirection = ref<'forward' | 'backward'>('forward');
    const loading = ref(false);
    const detailLoading = ref(false);
    const rollingBack = ref(false);
    const expandedView = ref(false);

    // Computed
    const selectedVersion = computed(() =>
        versions.value.length > 0
            ? versions.value[selectedIndex.value] ?? null
            : null
    );

    const isNewest = computed(
        () => selectedIndex.value === versions.value.length - 1
    );
    const isOldest = computed(() => selectedIndex.value === 0);

    // Set of top-level fields that changed vs previous version
    const diffFields = computed(() => changedFields(versionDiff.value));

    // Per-field text changes for inline word-level diffs
    const textChanges = computed(() => extractTextChanges(versionDiff.value));

    // The hydrated entry (same shape as SynthesizedDictionaryEntry) for the selected version
    const hydratedEntry = computed((): SynthesizedDictionaryEntry | null => {
        const content = versionDetail.value?.content;
        if (!content) return null;
        // The hydrated content from the backend has the same shape as a lookup response
        return content as unknown as SynthesizedDictionaryEntry;
    });

    // Debounced detail + diff fetch
    const fetchDetailAndDiff = useDebounceFn(async (index: number) => {
        const version = versions.value[index];
        if (!wordRef.value || !version) return;

        detailLoading.value = true;
        versionDetail.value = null;
        versionDiff.value = null;

        try {
            // Fetch hydrated detail (definitions, pronunciation, images resolved)
            const detailPromise = versionsApi.getVersion(
                wordRef.value,
                version.version,
                true, // hydrate
            );

            // Fetch hydrated diff vs previous version (text-level, not ID-level)
            const prevVersion =
                index > 0 ? versions.value[index - 1] : null;
            const diffPromise = prevVersion
                ? versionsApi
                      .diff(
                          wordRef.value,
                          prevVersion.version,
                          version.version,
                          true, // hydrate — diff on resolved text, not ObjectIds
                      )
                      .catch(() => null)
                : Promise.resolve(null);

            const [detail, diff] = await Promise.all([
                detailPromise,
                diffPromise,
            ]);

            versionDetail.value = detail;
            versionDiff.value = diff?.changes ?? null;
        } catch {
            versionDetail.value = null;
            versionDiff.value = null;
        } finally {
            detailLoading.value = false;
        }
    }, 150);

    // Watch selected version and fetch detail + diff
    watch(
        () => selectedIndex.value,
        (idx) => {
            if (isOpen.value && versions.value.length > 0) {
                fetchDetailAndDiff(idx);
            }
        }
    );

    // Collapse expanded view when navigating
    watch(selectedIndex, () => {
        expandedView.value = false;
    });

    // Open the overlay
    async function open() {
        if (!wordRef.value) return;
        isOpen.value = true;
        loading.value = true;
        expandedView.value = false;
        versionDetail.value = null;
        versionDiff.value = null;
        selectedIndex.value = 0;
        navigationDirection.value = 'forward';

        try {
            const data = await versionsApi.getHistory(wordRef.value);
            // Chronological order (oldest first)
            versions.value = [...(data.versions || [])].reverse();
            // Select the latest version (last in array)
            const latestIdx = versions.value.findIndex((v) => v.is_latest);
            selectedIndex.value =
                latestIdx >= 0 ? latestIdx : versions.value.length - 1;
        } catch {
            versions.value = [];
        } finally {
            loading.value = false;
        }
    }

    function close() {
        isOpen.value = false;
        expandedView.value = false;
        versions.value = [];
        versionDetail.value = null;
        versionDiff.value = null;
        selectedIndex.value = 0;
    }

    function selectVersion(index: number) {
        if (index < 0 || index >= versions.value.length) return;
        navigationDirection.value =
            index > selectedIndex.value ? 'forward' : 'backward';
        selectedIndex.value = index;
    }

    function navigateNext() {
        if (selectedIndex.value < versions.value.length - 1) {
            navigationDirection.value = 'forward';
            selectedIndex.value++;
        }
    }

    function navigatePrev() {
        if (selectedIndex.value > 0) {
            navigationDirection.value = 'backward';
            selectedIndex.value--;
        }
    }

    function toggleExpanded() {
        expandedView.value = !expandedView.value;
    }

    async function handleRollback() {
        if (!wordRef.value || !selectedVersion.value || !auth.isAdmin) return;
        rollingBack.value = true;
        try {
            await versionsApi.rollback(
                wordRef.value,
                selectedVersion.value.version
            );
            await open();
        } catch {
            // silently fail
        } finally {
            rollingBack.value = false;
        }
    }

    // Keyboard shortcuts
    const keys = useMagicKeys();

    whenever(
        () => keys.arrowleft.value && isOpen.value && !expandedView.value,
        () => navigatePrev()
    );
    whenever(
        () => keys.arrowright.value && isOpen.value && !expandedView.value,
        () => navigateNext()
    );
    whenever(
        () => keys.escape.value && isOpen.value,
        () => {
            if (expandedView.value) {
                expandedView.value = false;
            } else {
                close();
            }
        }
    );

    return {
        isOpen,
        versions,
        selectedIndex,
        selectedVersion,
        versionDetail,
        versionDiff,
        diffFields,
        textChanges,
        hydratedEntry,
        navigationDirection,
        loading,
        detailLoading,
        rollingBack,
        isNewest,
        isOldest,
        expandedView,

        open,
        close,
        selectVersion,
        navigateNext,
        navigatePrev,
        toggleExpanded,
        handleRollback,
    };
}
