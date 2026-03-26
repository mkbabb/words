import { ref } from 'vue';
import { wordlistApi } from '@/api/wordlists';
import { logger } from '@/utils/logger';
import type { ParsedWord } from './useWordlistFileParser';

export interface ReviewCandidate {
    id: string;
    sourceText: string;
    suggestedText: string;
    score: number;
    reason: string;
    sourceFrequency: number;
    suggestedFrequency: number;
}

/**
 * Calls the backend reconcile-preview endpoint and maps the response
 * into ReviewCandidate items that the WordPreviewList can render.
 */
export function useWordlistReconcilePreview() {
    const candidates = ref<ReviewCandidate[]>([]);
    const isLoading = ref(false);
    const error = ref<string | null>(null);

    async function reconcile(
        parsedWords: ParsedWord[],
        wordlistId?: string,
    ) {
        if (parsedWords.length === 0) {
            candidates.value = [];
            return;
        }

        isLoading.value = true;
        error.value = null;

        try {
            // Build entries in the format the backend expects:
            // list of strings or WordListEntryInput objects
            const entries = parsedWords.map((w) => ({
                source_text: w.text,
                resolved_text: w.resolvedText,
                frequency: w.frequency,
                notes: w.notes,
            }));

            const response = await wordlistApi.reconcilePreview(entries, wordlistId);

            // Map ambiguous + unresolved items into ReviewCandidate[]
            const result: ReviewCandidate[] = [];

            for (const item of response.ambiguous) {
                if (item.candidates.length === 0) continue;

                const topCandidate = item.candidates[0];
                result.push({
                    id: item.source_text.toLowerCase(),
                    sourceText: item.source_text,
                    suggestedText: topCandidate.word,
                    score: topCandidate.score,
                    reason: topCandidate.method === 'fuzzy'
                        ? 'Close fuzzy match found in dictionary'
                        : topCandidate.method === 'prefix'
                          ? 'Prefix match found in dictionary'
                          : `Match found via ${topCandidate.method}`,
                    sourceFrequency: item.frequency,
                    suggestedFrequency: 1,
                });
            }

            candidates.value = result.sort(
                (a, b) => b.score - a.score || b.sourceFrequency - a.sourceFrequency,
            );
        } catch (err) {
            logger.error('Reconcile preview failed:', err);
            error.value = err instanceof Error ? err.message : 'Reconcile preview failed';
            // Fall back to local-only candidates (empty — the old local heuristic
            // has been replaced by the backend endpoint)
            candidates.value = [];
        } finally {
            isLoading.value = false;
        }
    }

    return {
        candidates,
        isLoading,
        error,
        reconcile,
    };
}
