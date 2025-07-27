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
            'bg-gradient-to-br from-green-500 to-green-600',
            'text-white',
            'border-green-600'
        );
    } else if (score >= 0.8) {
        return cn(
            'bg-gradient-to-br from-green-400 to-green-500',
            'text-white',
            'border-green-500'
        );
    } else if (score >= 0.7) {
        return cn(
            'bg-gradient-to-br from-yellow-400 to-yellow-500',
            'text-white',
            'border-yellow-500'
        );
    } else if (score >= 0.6) {
        return cn(
            'bg-gradient-to-br from-orange-400 to-orange-500',
            'text-white',
            'border-orange-500'
        );
    } else {
        return cn(
            'bg-gradient-to-br from-red-400 to-red-500',
            'text-white',
            'border-red-500'
        );
    }
}

/**
 * Gets random delay for animation cycles
 */
export function getRandomAnimationDelay(min: number, max: number): number {
    return min + Math.random() * (max - min);
}