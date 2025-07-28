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
            'bg-gradient-to-br from-green-300 to-green-400',
            'text-green-900 dark:text-white',
            'border-green-400'
        );
    } else if (score >= 0.8) {
        return cn(
            'bg-gradient-to-br from-emerald-300 to-emerald-400',
            'text-emerald-900 dark:text-white',
            'border-emerald-400'
        );
    } else if (score >= 0.7) {
        return cn(
            'bg-gradient-to-br from-yellow-300 to-yellow-400',
            'text-yellow-900 dark:text-white',
            'border-yellow-400'
        );
    } else if (score >= 0.6) {
        return cn(
            'bg-gradient-to-br from-orange-300 to-orange-400',
            'text-orange-900 dark:text-white',
            'border-orange-400'
        );
    } else {
        return cn(
            'bg-gradient-to-br from-rose-300 to-rose-400',
            'text-rose-900 dark:text-white',
            'border-rose-400'
        );
    }
}

/**
 * Gets random delay for animation cycles
 */
export function getRandomAnimationDelay(min: number, max: number): number {
    return min + Math.random() * (max - min);
}