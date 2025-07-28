import { cn } from '@/utils';

/**
 * Formats example sentences with bold highlighting for the target word
 */
export function formatExampleHTML(example: string, word: string): string {
    // Create a case-insensitive regex to find the word and make it bold
    const regex = new RegExp(`\\b${word}\\b`, 'gi');
    return example.replace(
        regex,
        `<strong class="hover-word">${word}</strong>`
    );
}

/**
 * Gets the appropriate heatmap color class based on similarity score
 */
export function getHeatmapClass(score: number): string {
    if (score >= 0.9) {
        return cn(
            'bg-gradient-to-br from-green-300 to-green-400 dark:from-green-700 dark:to-green-800',
            'text-green-900 dark:text-green-100',
            'border-green-400 dark:border-green-600'
        );
    } else if (score >= 0.8) {
        return cn(
            'bg-gradient-to-br from-emerald-300 to-emerald-400 dark:from-emerald-700 dark:to-emerald-800',
            'text-emerald-900 dark:text-emerald-100',
            'border-emerald-400 dark:border-emerald-600'
        );
    } else if (score >= 0.7) {
        return cn(
            'bg-gradient-to-br from-yellow-300 to-yellow-400 dark:from-yellow-700 dark:to-yellow-800',
            'text-yellow-900 dark:text-yellow-100',
            'border-yellow-400 dark:border-yellow-600'
        );
    } else if (score >= 0.6) {
        return cn(
            'bg-gradient-to-br from-orange-300 to-orange-400 dark:from-orange-700 dark:to-orange-800',
            'text-orange-900 dark:text-orange-100',
            'border-orange-400 dark:border-orange-600'
        );
    } else {
        return cn(
            'bg-gradient-to-br from-rose-300 to-rose-400 dark:from-rose-700 dark:to-rose-800',
            'text-rose-900 dark:text-rose-100',
            'border-rose-400 dark:border-rose-600'
        );
    }
}

/**
 * Gets random delay for animation cycles
 */
export function getRandomAnimationDelay(min: number, max: number): number {
    return min + Math.random() * (max - min);
}