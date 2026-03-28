import { shallowRef, computed, watch } from 'vue';
import { useStores } from '@/stores';
import { useDebounceFn } from '@vueuse/core';
import type { WordListItem } from '@/types';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { applySortCriteria } from '../../utils/sortWords';

/**
 * Manages the debounced render cache that sits between the store's live results
 * and the virtualizer grid.
 *
 * Rapid search keystrokes update the store immediately, but this composable
 * collapses those updates into a single debounced snapshot so the virtualizer
 * doesn't thrash.
 */
export function useWordListCache() {
    const { searchBar } = useStores();
    const wordlistMode = useWordlistMode();

    // Filters from wordlist mode store
    const filters = computed(() => wordlistMode.wordlistFilters);

    // Sort criteria (writeable computed so the parent can bind v-model)
    const sortCriteria = computed({
        get: () => wordlistMode.wordlistSortCriteria,
        set: (value: any[]) => {
            wordlistMode.setWordlistSortCriteria(value);
        },
    });

    // -----------------------------------------------------------------------
    // Render cache
    // -----------------------------------------------------------------------

    const renderCache = shallowRef(new Map<string, WordListItem[]>());

    const cacheKey = computed(() => {
        const query = searchBar.searchQuery.trim().toLowerCase();
        return [
            wordlistMode.selectedWordlist ?? 'none',
            wordlistMode.resultsVersion,
            query,
            filters.value.showBronze,
            filters.value.showSilver,
            filters.value.showGold,
            filters.value.showHotOnly,
            filters.value.showDueOnly,
            wordlistMode.filters.minScore,
            sortCriteria.value
                .map((criterion) =>
                    'key' in criterion
                        ? `${criterion.key}:${criterion.order}`
                        : `${criterion.field}:${criterion.direction}`,
                )
                .join(','),
        ].join('|');
    });

    /**
     * Apply panel-level boolean filters on top of the store's filteredResults,
     * then sort.
     */
    function computeFilteredWords(): WordListItem[] {
        const key = cacheKey.value;
        const cached = renderCache.value.get(key);
        if (cached) return cached;

        const f = filters.value;
        const allMasteryShown = f.showBronze && f.showSilver && f.showGold;
        const noExtraFilters = !f.showHotOnly && !f.showDueOnly;

        let items: WordListItem[] =
            allMasteryShown && noExtraFilters
                ? (wordlistMode.filteredResults as WordListItem[])
                : (() => {
                      const now = f.showDueOnly ? Date.now() : 0;
                      return (wordlistMode.filteredResults as WordListItem[]).filter(
                          (word: any) => {
                              if (!allMasteryShown) {
                                  if (word.mastery_level === 'bronze' && !f.showBronze)
                                      return false;
                                  if (word.mastery_level === 'silver' && !f.showSilver)
                                      return false;
                                  if (word.mastery_level === 'gold' && !f.showGold)
                                      return false;
                              }
                              if (f.showHotOnly && word.temperature !== 'hot') return false;
                              if (f.showDueOnly) {
                                  if (!word.review_data?.next_review_date) return false;
                                  if (
                                      new Date(word.review_data.next_review_date).getTime() >
                                      now
                                  )
                                      return false;
                              }
                              return true;
                          },
                      );
                  })();

        if (sortCriteria.value.length > 0) {
            items = applySortCriteria([...items], sortCriteria.value);
        }

        const snapshot = [...items] as WordListItem[];
        renderCache.value.set(key, snapshot);
        if (renderCache.value.size > 24) {
            const firstKey = renderCache.value.keys().next().value;
            if (firstKey) renderCache.value.delete(firstKey);
        }
        return snapshot;
    }

    // Debounced snapshot the grid renders from
    const debouncedWords = shallowRef<WordListItem[]>([]);

    const flushGridWords = useDebounceFn(() => {
        debouncedWords.value = computeFilteredWords();
    }, 120);

    // Watch all inputs and debounce
    watch(
        [
            () => wordlistMode.filteredResults,
            filters,
            sortCriteria,
            () => wordlistMode.resultsVersion,
            () => searchBar.searchQuery,
            () => wordlistMode.selectedWordlist,
        ],
        () => {
            flushGridWords();
        },
        { immediate: true },
    );

    const currentWords = computed(() => debouncedWords.value);

    /** Call when the wordlist changes to clear stale cached data */
    const invalidateCache = () => {
        debouncedWords.value = [];
        renderCache.value = new Map();
    };

    return {
        currentWords,
        filters,
        sortCriteria,
        invalidateCache,
    };
}
