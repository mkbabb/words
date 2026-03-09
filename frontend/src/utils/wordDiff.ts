/**
 * Word-level diff utility.
 *
 * Splits two strings into word tokens, computes an LCS-based diff,
 * and returns segments tagged as equal / added / removed.
 *
 * When the two strings share very few words (< 30% similarity),
 * falls back to a clean "old → new" block display instead of
 * producing a jumbled interweaved result.
 */

export interface DiffSegment {
    type: 'equal' | 'added' | 'removed';
    text: string;
}

/** Minimum fraction of shared words for inline interweaved diff. */
const SIMILARITY_THRESHOLD = 0.3;

/** Tokenize text into word tokens (ignoring whitespace tokens for matching). */
function tokenize(text: string): string[] {
    return text.match(/\S+|\s+/g) ?? [];
}

/** Count only non-whitespace tokens. */
function wordCount(tokens: string[]): number {
    return tokens.filter((t) => t.trim().length > 0).length;
}

/**
 * Compute a word-level diff between two strings.
 * Returns an array of DiffSegments that, when concatenated, reproduce
 * the old text (equal + removed) and the new text (equal + added).
 *
 * When the texts are too dissimilar (< 30% shared words), returns
 * a simple [removed old] [added new] pair instead of interweaving.
 */
export function wordDiff(oldText: string, newText: string): DiffSegment[] {
    if (oldText === newText) {
        return oldText ? [{ type: 'equal', text: oldText }] : [];
    }
    if (!oldText) {
        return newText ? [{ type: 'added', text: newText }] : [];
    }
    if (!newText) {
        return [{ type: 'removed', text: oldText }];
    }

    const oldTokens = tokenize(oldText);
    const newTokens = tokenize(newText);

    // Compute LCS
    const lcs = longestCommonSubsequence(oldTokens, newTokens);

    // Check similarity: ratio of matched words to total words
    const totalWords = Math.max(wordCount(oldTokens), wordCount(newTokens), 1);
    const matchedWords = lcs.filter(
        ([oi]) => oldTokens[oi].trim().length > 0,
    ).length;
    const similarity = matchedWords / totalWords;

    // If texts are too different, show as clean replacement blocks
    if (similarity < SIMILARITY_THRESHOLD) {
        return [
            { type: 'removed', text: oldText },
            { type: 'added', text: newText },
        ];
    }

    // Build interweaved diff from LCS
    const segments: DiffSegment[] = [];
    let oi = 0;
    let ni = 0;

    for (const [lo, ln] of lcs) {
        if (oi < lo || ni < ln) {
            const removed = oldTokens.slice(oi, lo).join('');
            const added = newTokens.slice(ni, ln).join('');
            if (removed) segments.push({ type: 'removed', text: removed });
            if (added) segments.push({ type: 'added', text: added });
        }
        segments.push({ type: 'equal', text: oldTokens[lo] });
        oi = lo + 1;
        ni = ln + 1;
    }

    // Trailing tokens after last LCS match
    const removed = oldTokens.slice(oi).join('');
    const added = newTokens.slice(ni).join('');
    if (removed) segments.push({ type: 'removed', text: removed });
    if (added) segments.push({ type: 'added', text: added });

    return mergeAdjacentSegments(segments);
}

/** Merge consecutive segments of the same type. */
function mergeAdjacentSegments(segments: DiffSegment[]): DiffSegment[] {
    if (segments.length === 0) return segments;
    const merged: DiffSegment[] = [segments[0]];
    for (let i = 1; i < segments.length; i++) {
        const last = merged[merged.length - 1];
        if (last.type === segments[i].type) {
            last.text += segments[i].text;
        } else {
            merged.push({ ...segments[i] });
        }
    }
    return merged;
}

/**
 * Standard LCS on two arrays, returns pairs of matching indices.
 * Uses O(n*m) DP — fine for typical text lengths (< few thousand words).
 */
function longestCommonSubsequence(
    a: string[],
    b: string[],
): [number, number][] {
    const m = a.length;
    const n = b.length;

    const dp: number[][] = Array.from({ length: m + 1 }, () =>
        new Array(n + 1).fill(0),
    );

    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (a[i - 1] === b[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }

    const pairs: [number, number][] = [];
    let i = m;
    let j = n;
    while (i > 0 && j > 0) {
        if (a[i - 1] === b[j - 1]) {
            pairs.push([i - 1, j - 1]);
            i--;
            j--;
        } else if (dp[i - 1][j] >= dp[i][j - 1]) {
            i--;
        } else {
            j--;
        }
    }
    pairs.reverse();
    return pairs;
}
