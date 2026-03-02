import type { WordListItem } from '@/types';
import type { SortCriterion } from '@/types/wordlist';

const MASTERY_ORDER: Record<string, number> = {
    bronze: 0,
    silver: 1,
    gold: 2,
};

const TEMPERATURE_ORDER: Record<string, number> = {
    cold: 0,
    warm: 1,
    hot: 2,
};

/**
 * Pure sort function for wordlist items.
 *
 * Applies an ordered list of sort criteria. Each criterion is compared in turn;
 * ties on earlier criteria fall through to later ones.
 *
 * Supports both SimpleSortCriterion ({ key, order }) and
 * AdvancedSortCriterion ({ field, direction }) shapes.
 *
 * Always returns a new mutable array -- never mutates the input.
 */
export function applySortCriteria(
    words: readonly WordListItem[],
    criteria: readonly SortCriterion[]
): WordListItem[] {
    if (criteria.length === 0) return [...words];

    const sorted: WordListItem[] = [...words];

    sorted.sort((a, b) => {
        for (const criterion of criteria) {
            // Normalise the key across both criterion shapes
            const key: string =
                'key' in criterion
                    ? criterion.key
                    : 'field' in criterion &&
                        criterion.field === 'mastery_level'
                      ? 'mastery'
                      : 'field' in criterion &&
                          criterion.field === 'next_review'
                        ? 'next_review'
                        : 'field' in criterion && criterion.field === 'added_at'
                          ? 'created'
                          : 'word';

            let aVal: string | number;
            let bVal: string | number;

            switch (key) {
                case 'word':
                    aVal = a.word.toLowerCase();
                    bVal = b.word.toLowerCase();
                    break;
                case 'mastery':
                    aVal =
                        MASTERY_ORDER[
                            a.mastery_level as keyof typeof MASTERY_ORDER
                        ] || 0;
                    bVal =
                        MASTERY_ORDER[
                            b.mastery_level as keyof typeof MASTERY_ORDER
                        ] || 0;
                    break;
                case 'temperature':
                    aVal =
                        TEMPERATURE_ORDER[
                            a.temperature as keyof typeof TEMPERATURE_ORDER
                        ] || 0;
                    bVal =
                        TEMPERATURE_ORDER[
                            b.temperature as keyof typeof TEMPERATURE_ORDER
                        ] || 0;
                    break;
                case 'next_review':
                    aVal = new Date(
                        a.review_data?.next_review_date || 0
                    ).getTime();
                    bVal = new Date(
                        b.review_data?.next_review_date || 0
                    ).getTime();
                    break;
                case 'created':
                    aVal = new Date(a.added_date || 0).getTime();
                    bVal = new Date(b.added_date || 0).getTime();
                    break;
                default:
                    continue;
            }

            const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
            if (cmp === 0) continue; // tie -- fall through to next criterion

            const order =
                'order' in criterion ? criterion.order : criterion.direction;
            return order === 'desc' ? -cmp : cmp;
        }
        return 0;
    });

    return sorted;
}
