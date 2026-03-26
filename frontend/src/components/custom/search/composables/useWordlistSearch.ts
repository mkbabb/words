import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { wordlistApi } from '@/api';
import type { WordListItem, WordListSearchItem } from '@/types/wordlist';

/**
 * Wordlist mode search operations.
 *
 * Handles fetching wordlist words, searching within a wordlist,
 * pagination (load-more), and add/remove/batch mutations.
 */
export function useWordlistSearch() {
    const wordlistMode = useWordlistMode();

    // Track active wordlist abort controller
    let wordlistAbortController: AbortController | null = null;

    const cancelWordlistSearch = () => {
        if (wordlistAbortController) {
            wordlistAbortController.abort();
            wordlistAbortController = null;
        }
    };

    const executeWordlistFetch = async (
        wordlistId: string,
        offset = 0,
        limit = 50
    ): Promise<WordListItem[]> => {
        wordlistMode.setCurrentWordlistId(wordlistId);

        // Cancel any existing wordlist search
        cancelWordlistSearch();
        wordlistAbortController = new AbortController();

        // Capture generation BEFORE the async fetch — used to reject stale appends
        const fetchGeneration = wordlistMode.storeGeneration;
        const replace = offset === 0;

        try {
            const response = await wordlistApi.getWordlistWords(wordlistId, {
                offset,
                limit,
            });

            const items = (response.items || []) as WordListItem[];

            if (replace) {
                wordlistMode.setResults(items, true);
            } else {
                // Reject if a backward reset happened while this fetch was in-flight
                const accepted = wordlistMode.appendIfCurrent(items, fetchGeneration);
                if (!accepted) return [];
            }

            wordlistMode.setPagination({
                offset: offset + items.length,
                limit,
                total: response.total || items.length,
                hasMore: (response.total || 0) > offset + items.length,
            });

            return items;
        } catch (error: any) {
            if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
                return [];
            }

            wordlistMode.clearResults();
            throw error;
        } finally {
            wordlistAbortController = null;
        }
    };

    const executeWordlistSearchApi = async (
        wordlistId: string,
        queryText: string,
        offset = 0,
        limit = 50
    ): Promise<WordListItem[]> => {
        wordlistMode.setCurrentWordlistId(wordlistId);
        wordlistMode.setCurrentQuery(queryText);

        // Cancel any existing wordlist search
        cancelWordlistSearch();
        wordlistAbortController = new AbortController();

        const fetchGeneration = wordlistMode.storeGeneration;
        const replace = offset === 0;

        try {
            const response = await wordlistApi.searchWordlist(wordlistId, {
                query: queryText,
                max_results: limit,
                min_score: wordlistMode.filters.minScore,
                mode: wordlistMode.searchMode !== 'smart' ? wordlistMode.searchMode : undefined,
                offset,
                limit,
            });

            const items = (response.items || []) as WordListSearchItem[];

            if (replace) {
                wordlistMode.setResults(items as unknown as WordListItem[], true);
            } else {
                const accepted = wordlistMode.appendIfCurrent(items as unknown as WordListItem[], fetchGeneration);
                if (!accepted) return [];
            }

            wordlistMode.setPagination({
                offset: offset + items.length,
                limit,
                total: response.total || items.length,
                hasMore: (response.total || 0) > offset + items.length,
            });

            return items as unknown as WordListItem[];
        } catch (error: any) {
            if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
                return [];
            }

            wordlistMode.clearResults();
            throw error;
        } finally {
            wordlistAbortController = null;
        }
    };

    const loadMoreWordlist = async (): Promise<WordListItem[]> => {
        const { hasMore } = wordlistMode.pagination;
        const wordlistId = wordlistMode.currentWordlistId;
        if (!hasMore || !wordlistId) return [];

        const { offset, limit } = wordlistMode.pagination;
        const currentQuery = wordlistMode.currentQuery;

        if (currentQuery) {
            return await executeWordlistSearchApi(
                wordlistId,
                currentQuery,
                offset,
                limit
            );
        } else {
            return await executeWordlistFetch(wordlistId, offset, limit);
        }
    };

    /**
     * Re-fetch from a target offset when scrolling backward into evicted data.
     * Cancels in-flight fetches and resets the window to avoid interleaving.
     * Debounced: rapid scroll triggers are coalesced into a single fetch.
     */
    let backwardFetchTimer: ReturnType<typeof setTimeout> | null = null;
    const loadBeforeWordlist = (targetOffset: number): void => {
        // Debounce: wait 150ms after last call before fetching
        if (backwardFetchTimer) clearTimeout(backwardFetchTimer);
        backwardFetchTimer = setTimeout(async () => {
            backwardFetchTimer = null;
            const wordlistId = wordlistMode.currentWordlistId;
            if (!wordlistId) return;

            // Cancel any in-flight forward fetches
            cancelWordlistSearch();

            const fetchOffset = Math.max(0, targetOffset);
            const { limit, total } = wordlistMode.pagination;
            const fetchLimit = Math.max(limit, 50);

            try {
                const response = await wordlistApi.getWordlistWords(wordlistId, {
                    offset: fetchOffset,
                    limit: fetchLimit,
                });
                const items = (response.items || []) as WordListItem[];

                // Replace the entire window starting from the target offset
                wordlistMode.setResults(items, true);
                // Set windowStart since replace resets it to 0
                wordlistMode.setWindowStart(fetchOffset);

                // Update pagination to resume forward from here
                wordlistMode.setPagination({
                    offset: fetchOffset + items.length,
                    limit: fetchLimit,
                    total: total || items.length,
                    hasMore: (total || 0) > fetchOffset + items.length,
                });
            } catch {
                // Silently ignore — skeletons remain until next scroll settles
            }
        }, 150);
    };

    const addToWordlist = async (word: string): Promise<void> => {
        const wordlistId = wordlistMode.selectedWordlist;
        if (!wordlistId) {
            throw new Error('No wordlist selected');
        }
        await wordlistApi.addWords(wordlistId, [word]);
        // Refresh results to show the new word
        await executeWordlistFetch(wordlistId);
    };

    const removeFromWordlist = async (word: string): Promise<void> => {
        const wordlistId = wordlistMode.selectedWordlist;
        if (!wordlistId) {
            throw new Error('No wordlist selected');
        }
        await wordlistApi.removeWord(wordlistId, word);
        // Optimistic update: remove from store results
        const updated = [...wordlistMode.results].filter(
            (w: any) => w.word !== word
        );
        wordlistMode.setResults(updated as any);
    };

    const processBatchWordlist = async (
        words: string[],
        onProgress?: (completed: number, total: number) => void
    ): Promise<void> => {
        const wordlistId = wordlistMode.selectedWordlist;
        if (!wordlistId) {
            throw new Error('No wordlist selected');
        }

        for (let i = 0; i < words.length; i++) {
            await addToWordlist(words[i]);
            if (onProgress) {
                onProgress(i + 1, words.length);
            }
        }
    };

    return {
        executeWordlistFetch,
        executeWordlistSearchApi,
        loadMoreWordlist,
        loadBeforeWordlist,
        addToWordlist,
        removeFromWordlist,
        processBatchWordlist,
        cancelWordlistSearch,
    };
}
